import boto3
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from PIL import Image
import io

# Load environment variables from .env file
load_dotenv()

# Retrieve AWS credentials from environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

# AWS S3 client using credentials from .env
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def compress_image(image_data: bytes, max_size_kb: int = 200) -> bytes:
    img = Image.open(io.BytesIO(image_data))
    quality = 95
    while True:
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=quality)
        size_kb = buffer.tell() / 1024
        if size_kb <= max_size_kb or quality <= 5:
            return buffer.getvalue()
        quality -= 5

def upload_file_to_s3(bucket_name, subject, file: UploadFile):
    file_uuid = str(uuid.uuid4())
    object_key = f"questions/{subject.lower()}/{file_uuid}.png"

    try:
        # Read file content
        content = file.file.read()
        
        # Compress if needed
        if len(content) > 200 * 1024:  # if larger than 200kb
            content = compress_image(content)
            
        # Upload the file to S3
        s3.upload_fileobj(
            Fileobj=io.BytesIO(content),
            Bucket=bucket_name,
            Key=object_key,
            ExtraArgs={
                'ContentType': 'image/png'
            }
        )

        # Get the public URL of the uploaded file
        public_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
        return public_url

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")

@app.post("/upload/")
async def upload_image(subject: str, file: UploadFile = File(...)):
    bucket_name = "lumi-questions"
    
    # Upload the file and get the URL
    url = upload_file_to_s3(bucket_name, subject, file)

    # Return the URL in the response
    if url:
        return JSONResponse(content={"message": "File uploaded successfully", "url": url})
    else:
        raise HTTPException(status_code=500, detail="Failed to upload file")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)