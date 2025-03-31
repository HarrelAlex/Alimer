from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import time

load_dotenv()

genai.configure(api_key="AIzaSyBWBcGeC1oNYnrj22Y2KlvRjwCprobwD4c")

prompt = """You are a YouTube video summarizer. You will be taking the transcript text
and summarizing the entire video and providing the summary using sub-headings and in points
within 300 words. Please provide the summary of the text given here:  """

prompt_2 = """You are a YouTube video question answering chat bot. You are provided with the
youtube transcript of the video. Please answer the following question based on the transcript text provided: """

def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ""
        for i in transcript_text:
            transcript += " " + i["text"]
        return transcript
    except Exception as e:
        raise e

def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt + transcript_text)
    return response.text

def generate_gemini_qna(transcript_text, prompt, question):
    model = genai.GenerativeModel("gemini-pro")
    response1 = model.generate_content(prompt + transcript_text + question)
    return response1.text

def main():
    print("YouTube Video Query Solver")
    youtube_link = input("\nEnter YouTube Video Link: ")

    if youtube_link:
        video_id = youtube_link.split("=")[1]
        print(f"Video ID: {video_id}")
        print(f"Thumbnail URL: http://img.youtube.com/vi/{video_id}/0.jpg")

        transcript_text = extract_transcript_details(youtube_link)

        if transcript_text:
            summary = generate_gemini_content(transcript_text, prompt)
            print("\n## Detailed Notes:")
            print(summary)
            action = input("Do you want to ask a question? (yes/no): ").strip().lower()
            elif action == "yes":
                query = input("Enter your question: ")
                answer = generate_gemini_qna(transcript_text, prompt_2, query)
                print("\n## Answer:")
                print(answer)
            else:
                print("Exiting...")
        else:
            print("Failed to extract transcript.")
    else:
        print("No YouTube link provided.")

if __name__ == "__main__":
    main()