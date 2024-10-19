import logging
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import yt_dlp as youtube_dl
import os
import assemblyai as aai
import google.generativeai as genai
from .models import BlogPost
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Google Generative AI client
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    logger.error("ASSEMBLYAI_API_KEY is not set in environment variables")
    
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
            logger.info(f"Received request to generate blog for link: {yt_link}")
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Invalid data sent: {e}")
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        try:
            # Use ThreadPoolExecutor to run tasks concurrently
            with ThreadPoolExecutor(max_workers=3) as executor:
                title_future = executor.submit(yt_title, yt_link)
                transcription_future = executor.submit(get_transcription, yt_link)
                
                title = title_future.result()
                transcription = transcription_future.result()

            if not transcription or len(transcription) < 50:  # Adjust the minimum length as needed
                logger.error(f"Transcription too short or empty: {transcription}")
                return JsonResponse({"error": "Transcription too short or failed"}, status=500)

            blog_content = generate_blog_from_transcription(transcription)
            if not blog_content:
                logger.error("Failed to generate blog content")
                return JsonResponse({"error": "Failed to generate blog content"}, status=500)

            new_blog_article = BlogPost.objects.create(
                user=request.user,
                youtube_title=title,
                youtube_link=yt_link,
                generated_content=blog_content,
            )
            new_blog_article.save()
            
            cleanup_audio_files()
            logger.info("Blog generated and saved successfully")
            return JsonResponse({"content": blog_content}, status=200)
        except Exception as e:
            logger.exception(f"Error in generate_blog: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    try:
        ydl = youtube_dl.YoutubeDL()
        info = ydl.extract_info(link, download=False)
        title = info.get('title', 'Unknown Title')
        logger.info(f"Retrieved YouTube title: {title}")
        return title
    except Exception as e:
        logger.error(f"Error getting YouTube title: {e}")
        return "Unknown Title"

def cleanup_audio_files():
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
    if not os.path.exists(audio_dir):
        logger.warning(f"Audio directory does not exist: {audio_dir}")
        return
    try:
        for filename in os.listdir(audio_dir):
            file_path = os.path.join(audio_dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        logger.info("Audio files cleaned up successfully")
    except Exception as e:
        logger.error(f'Failed to cleanup audio files. Reason: {e}')

def download_audio(link):
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
    base_filename = 'audio'
    final_audio_path = os.path.join(audio_dir, f'{base_filename}.mp3')
    
    os.makedirs(audio_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(audio_dir, f'{base_filename}.%(ext)s'),
        'postprocessor_args': [
            '-loglevel', 'quiet',
            '-ab', '192k',
            '-y',
        ],
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        
        # Check for the file with .mp3 extension
        if os.path.exists(final_audio_path):
            logger.info(f"Audio downloaded successfully: {final_audio_path}")
            return final_audio_path
        else:
            # If not found, look for any file starting with 'audio' in the directory
            for filename in os.listdir(audio_dir):
                if filename.startswith(base_filename):
                    full_path = os.path.join(audio_dir, filename)
                    logger.info(f"Audio downloaded successfully: {full_path}")
                    return full_path
            
            logger.error(f"Audio file not found after download")
            return None
    except Exception as e:
        logger.error(f"Error during audio download: {e}")
    
    return None

def get_transcription(link):
    audio_file = download_audio(link)
    if not audio_file:
        logger.error("Failed to download audio file")
        return None
    
    try:
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        
        # Check if the file exists before transcribing
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return None
        
        transcript = transcriber.transcribe(audio_file)

        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"Transcription error: {transcript.error}")
            return None
        else:
            logger.info("Transcription completed successfully")
            return transcript.text
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return None
    finally:
        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
                logger.info(f"Removed audio file: {audio_file}")
            else:
                logger.warning(f"Could not remove audio file (not found): {audio_file}")
        except Exception as e:
            logger.error(f"Error while trying to remove audio file: {e}")
def generate_blog_from_transcription(transcription):
    try:
        logger.info("Generating blog content from transcription")
        response = model.generate_content(
            f"Create a well-structured blog article based on the following transcript. "
            f"The article should include the following sections: Introduction, Main Points, Analysis, and Conclusion. "
            f"Use clear headings and subheadings. Break down complex ideas into bullet points or numbered lists. "
            f"Ensure the article is engaging and easy to read. Avoid making it sound like it's based on a YouTube transcript, and instead, make it a coherent blog post:\n\n{transcription}\n\n"
            f"**Structure**:\n"
            f"1. **Introduction**: Briefly introduce the topic and set the tone for the article.\n"
            f"2. **Main Points**: Highlight the key points from the transcript. Use bullet points or subheadings for clarity.\n"
            f"3. **Analysis**: Offer an in-depth analysis of the topic. Discuss the implications, interpretations, or lessons learned.\n"
            f"4. **Conclusion**: Summarize the main ideas and provide a closing thought or call to action.\n\n"
            f"**Article**:"
        )
        generated_content = response.text
        if not generated_content:
            logger.error("No content generated from AI model")
            return None
        logger.info(f"Blog content generated successfully (length: {len(generated_content)} characters)")
        return generated_content
    except Exception as e:
        logger.exception(f"Error generating blog content: {e}")
        return None

@login_required
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

@login_required
def blog_details(request, pk):
    try:
        blog_article_detail = BlogPost.objects.get(id=pk)
        if request.user == blog_article_detail.user:
            return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
        else:
            return redirect('/')
    except BlogPost.DoesNotExist:
        return redirect('/')

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('Username')
        password = request.POST.get('Password')
        if username and password:
            # Check if the user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return render(request, 'login.html', {'error': 'User does not exist. Please sign up first.'})
            
            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
<<<<<<< HEAD
                # Return an 'invalid login' error message.
                return render(request, 'login.html', {'error': 'Invalid password'})
=======
                return render(request, 'login.html', {'error_message': 'Invalid username or password'})
>>>>>>> temp_branch
        else:
            return render(request, 'login.html', {'error_message': 'Please provide both username and password'})
    else:
        return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

def user_signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        repeat_password = request.POST.get("repeat_password")

        if password == repeat_password:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except Exception as e:
                error_message = f'Error creating account: {e}'
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = "Passwords do not match"
            return render(request, 'signup.html', {'error_message': error_message})
    return render(request, "signup.html")

@csrf_exempt
def delete_all_blogs(request):
    if request.method == 'POST':
        BlogPost.objects.all().delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@csrf_exempt
def delete_selected_blogs(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            blog_ids = data.get('blog_ids', [])
            BlogPost.objects.filter(id__in=blog_ids).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
