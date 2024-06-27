from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import os
import assemblyai as aai
from openai import OpenAI
from .models import BlogPost


# Create your views here.

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

        # Use OpenAI to generate blog content
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({"error": "API key limit is reached, purchase plan to continue...."}, status=500)

        # Save blog article to database (not implemented in this code snippet)
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()


        # Return blog article as response 
        return JsonResponse({"content": blog_content}, status=200)  

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    os.remove(audio_file)

    return transcript.text

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()

    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request,"all-blogs.html",{'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

from openai import OpenAI, OpenAIError

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))



def generate_blog_from_transcription(transcription):
    try:
        # Construct the prompt
        prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article. Write it based on the transcript, but don't make it look like a YouTube video. Make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

        response = client.completions.create(
            model='gpt-3.5-turbo-instruct',
            prompt=prompt,
            max_tokens=1000
        )
        # Extracting the completion
        completion = response.choices[0]
        generated_content = completion.text

        print("*"*5,generated_content)       # If the content is empty or null, return None
        if not generated_content:
            # logger.error("API key limit is reached.")
            return JsonResponse({"error": "API key limit is reached, purchase plan to continue...."}, status=500)


        # Split the generated content into paragraphs
        paragraphs = generated_content.split('\n\n')

        # Create a new text with paragraphs after every 3 paragraphs
        generated_content = '\n\n'.join([''.join(sublist) for sublist in paragraphs])
    
    except OpenAIError as e:
        # Handle OpenAI API errors
        print("API key limit is reached, purchase plan to continue....")
        print(f"Error generating blog: {e}")  # Log the error for debugging
        return None
    
def user_login(request):
    if request.method == 'POST':
        username = request.POST['Username']
        password = request.POST['Password']

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
        Username = request.POST["Username"]
        Email = request.POST["Email"]
        Password = request.POST["Password"]
        RepeatPassword = request.POST["RepeatPassword"]

        if Password == RepeatPassword:
            try:
                user = User.objects.create_user(Username, Email, Password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = "Password do not match"
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