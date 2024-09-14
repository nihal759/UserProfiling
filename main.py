from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status,Depends
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse,HTMLResponse
import os
import pyodbc
import httpx
import logging
from datetime import datetime
import joblib
import pandas as pd
import numpy as np
from database import create_connection
from model import create_engine
from typing import List
app = FastAPI()

# Load the trained model and interaction matrix
svd = joblib.load('svd_model.pkl')
interaction_matrix = joblib.load('interaction_matrix.pkl')

# Create a database connection
DATABASE_URL = "mssql+pyodbc://DESKTOP-K8BIO91\\SQLEXPRESS/autodetect?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(DATABASE_URL)

# YouTube API configuration
YOUTUBE_API_KEY = "AIzaSyCdrBM2PNQzamCRdL-FwHmPdiSFkTjW3tM"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.get("/index")
async def read_root():
    file_path = "templates/index.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return {"error": "File not found"}



@app.post("/submit-profile")
async def submit_profile(
    full_name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    dob: str = Form(...),
    categories: List[str] = Form(...),
    profession: List[str] = File(None),
    additional_comments: str = Form(...),
    profile_picture: UploadFile = File(None)
):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Read profile picture if it exists
        profile_picture_data = None
        if profile_picture:
            profile_picture_data = profile_picture.file.read()

        # Convert lists to comma-separated strings
        categories_str = ','.join(categories)
        profession_str = ','.join(profession)

        # Insert data into the database
        cursor.execute('''
            INSERT INTO user_profiles (full_name, email, username, dob, categories, profession, profile_picture, additional_comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (full_name, email, username, dob, categories_str, profession_str, profile_picture_data, additional_comments))

        conn.commit()
        cursor.close()
        conn.close()

        # Redirect to video.html after successful submission
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logging.error(f"Error in submit_profile: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    
    
@app.get("/recommendations")
async def get_recommendations(query: str):
    try:
        # Construct the URL for the YouTube API
        params = {
            "part": "snippet",
            "q": query,
            "key": YOUTUBE_API_KEY,
            "maxResults": 5,  # Fetch a limited number of results for simplicity
            "type": "video"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(YOUTUBE_API_URL, params=params)
            response.raise_for_status()  # Raise HTTP errors
            video_data = response.json()

            if 'error' in video_data:
                return JSONResponse(content={"error": video_data['error']['message']}, status_code=response.status_code)

            # Extract video information
            videos = video_data.get('items', [])
            video_items = [
                {
                    'title': video['snippet']['title'],
                    'description': video['snippet']['description'],
                    'thumbnail': video['snippet']['thumbnails']['default']['url'],
                    'video_id': video['id']['videoId']
                }
                for video in videos
            ]

            return {"items": video_items}
    except Exception as e:
        logging.error(f"Error in get_recommendations: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/search")
async def search_videos(query: str, pageToken: str = "", maxResults: int = 10):
    params = {
        "part": "snippet",
        "q": query,
        "key": YOUTUBE_API_KEY,
        "maxResults": maxResults,
        "pageToken": pageToken,
        "type": "video"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(YOUTUBE_API_URL, params=params)
            response.raise_for_status()  # Raise HTTP errors
            data = response.json()

            if 'error' in data:
                if data['error']['code'] == 403:
                    logging.error(f"YouTube API Error 403: {data['error']['message']}")
                    return JSONResponse(content={"error": "API key error or quota exceeded."}, status_code=403)
                logging.error(f"YouTube API Error: {data['error']['message']}")
                return JSONResponse(content={"error": data['error']['message']}, status_code=400)
                
            return JSONResponse(content=data)
    except httpx.HTTPStatusError as http_error:
        logging.error(f"HTTP Error: {str(http_error)}")
        return JSONResponse(content={"error": str(http_error)}, status_code=http_error.response.status_code)
    except Exception as e:
        logging.error(f"Unexpected Error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/video")
async def serve_video(user_id: int, profession: str):
    try:
        # Logging input parameters for debugging
        logging.info(f"Received request with user_id: {user_id}, profession: {profession}")

        # Determine the search query based on the user's profession
        profession_queries = {
            "Teacher": "education",
            "Student": "student",
            # Add more professions and queries as needed
        }
        
        query = profession_queries.get(profession, "popular")

        # Construct the URL for the YouTube API
        params = {
            "part": "snippet",
            "q": query,
            "key": YOUTUBE_API_KEY,
            "maxResults": 5,  # Fetch a limited number of results for simplicity
            "type": "video"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(YOUTUBE_API_URL, params=params)
            response.raise_for_status()  # Raise HTTP errors
            video_data = response.json()

            if 'error' in video_data:
                if video_data['error']['code'] == 403:
                    logging.error(f"YouTube API Error 403: {video_data['error']['message']}")
                    return JSONResponse(content={"error": "API key error or quota exceeded."}, status_code=403)
                logging.error(f"YouTube API Error: {video_data['error']['message']}")
                return JSONResponse(content={"error": video_data['error']['message']}, status_code=400)

            # Extract video information
            videos = video_data.get('items', [])
            video_items = [
                {
                    'title': video['snippet']['title'],
                    'description': video['snippet']['description'],
                    'thumbnail': video['snippet']['thumbnails']['default']['url'],
                    'video_id': video['id']['videoId']
                }
                for video in videos
            ]

            # Serve the HTML page with the video data
            file_path = r"D:\userprofiling\templates\vedio.html"  # Ensure this path is correct
            if os.path.exists(file_path):
                # Add video data to the HTML response
                with open(file_path, 'r') as file:
                    html_content = file.read()
                    html_content = html_content.replace("{{videos}}", str(video_items))
                return HTMLResponse(content=html_content)
            else:
                return JSONResponse(content={"error": "File not found"}, status_code=404)

    except Exception as e:
        logging.error(f"Error in serve_video: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/")
async def login_form():
    file_path = "templates/login.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return {"error": "File not found"}

@app.post("/login")
async def login(username: str = Form(...), email: str = Form(...)):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM admin WHERE name = ? AND email = ?
        ''', (username, email))
        admin = cursor.fetchone()
        
        if admin:
            cursor.close()
            conn.close()
            return RedirectResponse(url="/admin", status_code=303)
        cursor.execute('''
            SELECT id, profession FROM user_profiles
            WHERE username = ? AND email = ? 
        ''', (username, email))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            user_id, profession = user

            # Record interaction when user logs in
            await record_interaction(user_id=user_id, video_id=None, search_query=None, watched=False)

            return RedirectResponse(url=f"/video?user_id={user_id}&profession={profession}", status_code=303)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    except Exception as e:
        logging.error(f"Error in login: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/record_interaction")
async def record_interaction(
    user_id: int,
    video_id: int = None,
    search_query: str = None,
    watched: bool = False,
):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Convert boolean to BIT (0 or 1) for SQL Server
        watched_value = 1 if watched else 0

        # Insert interaction data into the database
        cursor.execute('''
            INSERT INTO user_interactions (user_id, video_id, search_query, watched, interaction_timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, video_id, search_query, watched_value, datetime.now()))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Interaction recorded successfully"}
    except Exception as e:
        logging.error(f"Error in record_interaction: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)



from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from fastapi import Request
templates = Jinja2Templates(directory="templates")
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT full_name, email, username, dob, categories, additional_comments, profession
        FROM user_profiles
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # Convert rows to a list of dictionaries
    users = [
        {
            "full_name": row.full_name,
            "email": row.email,
            "username": row.username,
            "dob": row.dob,
            "categories": row.categories,
            "additional_comments": row.additional_comments,
            "profession": row.profession
        }
        for row in rows
    ]
    
    return templates.TemplateResponse("admin.html", {"request": request, "users": users})





@app.get("/admin/update/{username}", response_class=HTMLResponse)
async def update_user_form(request: Request, username: str):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT full_name, email, username, dob, categories, additional_comments, profession
        FROM user_profiles
        WHERE username = ?
    """, (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        user = {
            "full_name": row.full_name,
            "email": row.email,
            "username": row.username,
            "dob": row.dob,
            "categories": row.categories,
            "additional_comments": row.additional_comments,
            "profession": row.profession
        }
        return templates.TemplateResponse("update_user.html", {"request": request, "user": user})
    else:
        return {"error": "User not found"}

@app.post("/admin/update/{username}")
async def update_user(username: str, full_name: str = Form(...), email: str = Form(...), dob: str = Form(...),
                      categories: str = Form(...), additional_comments: str = Form(...), profession: str = Form(...)):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_profiles
        SET full_name = ?, email = ?, dob = ?, categories = ?, additional_comments = ?, profession = ?
        WHERE username = ?
    """, (full_name, email, dob, categories, additional_comments, profession, username))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/admin/delete/{username}")
async def delete_user(username: str):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM user_profiles
        WHERE username = ?
    """, (username,))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/admin", status_code=303)