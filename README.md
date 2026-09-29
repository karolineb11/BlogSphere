# BlogSphere
Python + Streamlit + MySQL blogging platform with accounts, post CRUD, search, categories, comments, likes, bookmarks, profiles, and admin moderation.

## Run
1. Create the `blogsphere` database and tables using the SQL provided in the ChatGPT instructions.
2. Install: `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and enter your local MySQL password.
4. Run: `streamlit run app.py`

Never commit secrets. Use an online database and hosted secrets for deployment.