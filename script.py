from pytube import YouTube

# Input the YouTube video URL
url = "https://youtu.be/hxOApe1P9dM"  # Use the base URL

try:
    # Create a YouTube object
    yt = YouTube(url)

    # Print available streams for debugging
    print("Available streams:")
    for stream in yt.streams:
        print(stream)

    # Filter for audio streams and select the first one
    audio_stream = yt.streams.filter(only_audio=True).first()

    if audio_stream is None:
        print("No audio streams available for this video.")
    else:
        # Download the audio file
        print(f"Downloading audio from: {yt.title}")
        audio_file = audio_stream.download()

        # Optionally, rename the file to .mp3
        base, ext = os.path.splitext(audio_file)
        new_file = base + '.mp3'
        os.rename(audio_file, new_file)

        print(f"{yt.title} has been successfully downloaded as an MP3.")
except Exception as e:
    print(f"An error occurred: {e}")
