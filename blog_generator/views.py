from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
import yt_dlp as youtube_dl
import os
import assemblyai as aai
import google.generativeai as genai
from .models import BlogPost
from django.conf import settings


# Initialize Google Generative AI client
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        # Get YouTube title
        title = yt_title(yt_link)

        # Get transcription
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({"error": "Failed to get transcript"}, status=500)

        # Use Google Generative AI to generate blog content
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({"error": "Failed to generate blog content"}, status=500)

        # Save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()

        # Return blog article as response
        return JsonResponse({"content": blog_content}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    try:
        # Create a YT-DLP object with the given URL
        ydl = youtube_dl.YoutubeDL()
        
        # Extract information from the video URL
        info = ydl.extract_info(link, download=False)
        
        # Retrieve and print the video title
        title = info.get('title', 'Unknown Title')
        print("*" * 10, title)
        return title
    except Exception as e:
        print(f"Error getting YouTube title: {e}")
        return "Unknown Title"
def get_transcription(link):
    audio_file = download_audio(link)
    #path = os.path.join(settings.MEDIA_ROOT)
    if not audio_file:
        return None
    
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    os.remove(audio_file)

    return transcript.text

def download_audio(link):
    # Define the final audio path
    final_audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', 'audio.mp3')
    extracted_audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', 'audio.mp3')  # Adjust if needed

    # Ensure the directory exists
    os.makedirs(os.path.dirname(final_audio_path), exist_ok=True)

    # Define options for yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': final_audio_path,
        'postprocessor_args': [
            '-loglevel', 'quiet',
            '-ab', '192k',
            '-y',  # Overwrite output files without asking
        ],
    }

    try:
        # Download the audio
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        
        # Ensure the renamed file is accessible
        if not os.path.exists(extracted_audio_path):
            extracted_audio_path += '.mp3'
            
        return extracted_audio_path
    except youtube_dl.DownloadError as e:
        print(f"Error during download: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return None

def generate_blog_from_transcription(transcription):
    try:
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
            return None

        # Return the generated content
        return generated_content
    
    except Exception as e:
        print(f"Error generating blog content: {e}")
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

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message})

    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect("/")

def user_signup(request):
    if request.method == "POST":
        username = request.POST.get("Username")
        email = request.POST.get("Email")
        password = request.POST.get("Password")
        repeat_password = request.POST.get("RepeatPassword")

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
