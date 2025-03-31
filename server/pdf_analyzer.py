import pdfplumber
import os
import json
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer, util
import ollama
import torch

# Function to extract text from a PDF and save it to a text file
def extract_text_from_pdf(pdf_path, output_txt_file):
    try:
        # Check if the file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"The file '{pdf_path}' does not exist.")
        
        # Check if the file is a PDF
        if not pdf_path.lower().endswith('.pdf'):
            raise ValueError("The file is not a PDF.")
        
        extracted_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append({
                        "page": page_num + 1,
                        "text": text.strip()
                    })
        
        # Save the extracted text to a structured text file
        with open(output_txt_file, "w", encoding="utf-8") as f:
            json.dump(extracted_text, f, indent=4)
        
        print(f"Text extracted and saved to {output_txt_file}")
        return extracted_text
    except Exception as e:
        print(f"Error reading the PDF: {e}")
        return []

# Function to load the structured text file
def load_text_from_file(txt_file):
    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading text file: {e}")
        return []

# Function to chunk text into smaller parts
def chunk_text(text_data, chunk_size=500, overlap=100):
    chunks = []
    for entry in text_data:
        words = entry["text"].split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append({
                "page": entry["page"],
                "text": chunk
            })
    return chunks

# Function to initialize semantic search
def initialize_tools():
    print("Loading semantic search model. Please wait...")
    
    # Use a more robust embedding model for longer documents
    retriever_model = SentenceTransformer('all-mpnet-base-v2')
    
    print("Semantic search model loaded successfully!")
    return retriever_model

# Function to perform semantic search
def retrieve_relevant_context(query, text_chunks, retriever_model, top_k=5):
    # Ensure CUDA is used if available
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    retriever_model = retriever_model.to(device)
    
    query_embedding = retriever_model.encode(query, convert_to_tensor=True).to(device)
    chunk_texts = [chunk["text"] for chunk in text_chunks]
    chunk_embeddings = retriever_model.encode(chunk_texts, convert_to_tensor=True).to(device)
    
    # Compute cosine similarity between query and chunks
    scores = util.pytorch_cos_sim(query_embedding, chunk_embeddings)[0]
    
    # Ensure top_k does not exceed the number of chunks
    top_k = min(top_k, len(scores))
    
    if top_k == 0:
        return []  # No relevant context found
    
    top_results = scores.topk(k=top_k)
    relevant_chunks = [text_chunks[idx] for idx in top_results.indices]
    return relevant_chunks

# Function to generate an answer using local Ollama model
def generate_answer(prompt):
    try:
        # Use Mistral 7B as a capable local model
        response = ollama.chat(
            model='mistral',
            messages=[
                {
                    'role': 'system', 
                    'content': 'You are a helpful assistant that answers questions based strictly on the provided context. If the information is not in the context, say you do not know.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 500
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        print(f"\nChatbot: An error occurred while generating the answer: {e}")
        return "Sorry, I couldn't generate an answer due to a local model error."

# Function to process chunks in parallel
def process_chunks(query, text_chunks, retriever_model):
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(retrieve_relevant_context, query, [chunk], retriever_model) for chunk in text_chunks]
        relevant_contexts = [future.result() for future in futures]
    return [chunk for sublist in relevant_contexts for chunk in sublist]  # Flatten the list

# Chatbot interaction
def chatbot_interaction(text_chunks, retriever_model):
    print("\nChatbot: What do you want to learn more about this PDF?")
    print("(Type 'exit' to end the chat.)")
    
    while True:
        user_query = input("\nYou: ").strip()
        if user_query.lower() == "exit":
            print("\nChatbot: Goodbye!")
            break
        
        # Retrieve relevant context in parallel
        relevant_chunks = process_chunks(user_query, text_chunks, retriever_model)
        
        if relevant_chunks:
            print("\nChatbot: Let me generate an answer for you...")
            
            # Generate an answer using the retrieved context
            relevant_context = " ".join([chunk["text"] for chunk in relevant_chunks])
            prompt = f"Context: {relevant_context}\nQuestion: {user_query}\nProvide a detailed answer based only on the given context:"
            answer = generate_answer(prompt)
            
            print(f"\nChatbot: {answer}")
        else:
            print("\nChatbot: Sorry, I couldn't find any relevant information in the document.")

# Main program
if __name__ == "__main__":
    # Specify the uploaded PDF path and output text file
    pdf_file = r"C:\Users\Steve Paul Chully\Documents\Experion Resume.pdf"  # Replace with your PDF path
    output_txt_file = "extracted_text.json"

    print("Analyzing the PDF. Please wait...")
    extracted_text = extract_text_from_pdf(pdf_file, output_txt_file)

    if extracted_text:
        print("PDF analysis complete. Loading tools...")
        retriever_model = initialize_tools()
        
        # Load the extracted text from the text file
        text_chunks = chunk_text(extracted_text, chunk_size=750, overlap=150)
        
        # Start chatbot interaction
        chatbot_interaction(text_chunks, retriever_model)
    else:
        print("Failed to analyze the PDF. Please check the file and try again.")