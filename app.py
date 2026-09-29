import streamlit as st
import pandas as pd
import hashlib, hmac, os
from database import query

st.set_page_config(page_title="BlogSphere",page_icon="📝",layout="wide")
if "user" not in st.session_state: st.session_state.user=None
if "page" not in st.session_state: st.session_state.page="Home"
if "post_id" not in st.session_state: st.session_state.post_id=None

def hash_pw(pw):
    salt=os.urandom(16)
    key=hashlib.pbkdf2_hmac("sha256",pw.encode(),salt,200000)
    return salt.hex()+"$"+key.hex()

def check_pw(pw,stored):
    try:
        salt,key=stored.split("$",1)
        actual=hashlib.pbkdf2_hmac("sha256",pw.encode(),bytes.fromhex(salt),200000)
        return hmac.compare_digest(actual.hex(),key)
    except (ValueError,AttributeError): return False

def register():
    st.title("Create account")
    with st.form("register"):
        name=st.text_input("Name")
        email=st.text_input("Email")
        pw=st.text_input("Password",type="password")
        confirm=st.text_input("Confirm password",type="password")
        ok=st.form_submit_button("Register")
    if ok:
        if not name.strip() or not email.strip() or not pw: st.error("Fill in all fields.")
        elif pw!=confirm: st.error("Passwords do not match.")
        elif len(pw)<8: st.error("Password must be at least 8 characters.")
        elif query("SELECT user_id FROM users WHERE email=%s",(email.strip().lower(),),True):
            st.error("Email already registered.")
        else:
            query("INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
                  (name.strip(),email.strip().lower(),hash_pw(pw)))
            st.success("Account created. Please log in.")
            st.session_state.page="Login"

def login():
    st.title("Login")
    with st.form("login"):
        email=st.text_input("Email")
        pw=st.text_input("Password",type="password")
        ok=st.form_submit_button("Login")
    if ok:
        rows=query("SELECT * FROM users WHERE email=%s",(email.strip().lower(),),True)
        if rows and check_pw(pw,rows[0]["password"]):
            st.session_state.user=rows[0]; st.session_state.page="Home"; st.rerun()
        else: st.error("Invalid email or password.")

def posts(search="",category="All",mine=False,bookmarks=False):
    uid=st.session_state.user["user_id"] if st.session_state.user else -1
    sql="""SELECT p.*,u.name author FROM posts p JOIN users u ON p.user_id=u.user_id
           WHERE (p.title LIKE %s OR p.content LIKE %s OR COALESCE(p.tags,'') LIKE %s OR u.name LIKE %s)"""
    pat="%"+search+"%"; args=[pat,pat,pat,pat]
    if category!="All": sql+=" AND p.category=%s"; args.append(category)
    if mine: sql+=" AND p.user_id=%s"; args.append(uid)
    if bookmarks:
        sql+=" AND p.post_id IN (SELECT post_id FROM bookmarks WHERE user_id=%s)"; args.append(uid)
    sql+=" ORDER BY p.created_at DESC"
    return query(sql,tuple(args),True)

def show_posts(items):
    for p in items:
        likes=query("SELECT COUNT(*) n FROM likes WHERE post_id=%s",(p["post_id"],),True)[0]["n"]
        comments=query("SELECT COUNT(*) n FROM comments WHERE post_id=%s",(p["post_id"],),True)[0]["n"]
        with st.container(border=True):
            st.subheader(p["title"])
            st.caption(f"By {p['author']} • {p['created_at']} • {p.get('category') or 'General'}")
            if p.get("tags"): st.caption("🏷️ "+p["tags"])
            st.write(p["content"][:350]+("…" if len(p["content"])>350 else ""))
            st.caption(f"❤️ {likes} likes · 💬 {comments} comments")
            if st.button("Read / interact",key=f"open{p['post_id']}"):
                st.session_state.post_id=p["post_id"]; st.session_state.page="Post"; st.rerun()
            if st.session_state.user:
                uid=st.session_state.user["user_id"]
                saved=query("SELECT bookmark_id FROM bookmarks WHERE user_id=%s AND post_id=%s",(uid,p["post_id"]),True)
                if st.button("Remove bookmark" if saved else "🔖 Bookmark",key=f"save{p['post_id']}"):
                    if saved: query("DELETE FROM bookmarks WHERE user_id=%s AND post_id=%s",(uid,p["post_id"]))
                    else: query("INSERT IGNORE INTO bookmarks(user_id,post_id) VALUES(%s,%s)",(uid,p["post_id"]))
                    st.rerun()

def home():
    st.title("📝 BlogSphere")
    st.write("Share ideas, discover stories, and join the conversation.")
    allp=query("SELECT DISTINCT category FROM posts WHERE category IS NOT NULL AND category<>''",fetch=True)
    cats=["All"]+[r["category"] for r in allp]
    a,b=st.columns([3,1]); search=a.text_input("🔍 Search posts, authors, or tags")
    cat=b.selectbox("Category",cats)
    items=posts(search,cat)
    if not items: st.info("No posts yet. Start writing!")
    show_posts(items)

def editor(edit=None):
    st.title("Edit post" if edit else "✍️ Create a post")
    with st.form("editor"):
        title=st.text_input("Title",edit["title"] if edit else "")
        category=st.text_input("Category",(edit.get("category") or "") if edit else "")
        tags=st.text_input("Tags, comma-separated",(edit.get("tags") or "") if edit else "")
        content=st.text_area("Content",edit["content"] if edit else "",height=260)
        ok=st.form_submit_button("Save changes" if edit else "Publish")
    if ok:
        if not title.strip() or not content.strip(): st.error("Title and content are required.")
        elif edit:
            query("UPDATE posts SET title=%s,category=%s,tags=%s,content=%s WHERE post_id=%s AND user_id=%s",
                  (title.strip(),category.strip(),tags.strip(),content.strip(),edit["post_id"],st.session_state.user["user_id"]))
            st.session_state.page="My Posts"; st.rerun()
        else:
            query("INSERT INTO posts(user_id,title,content,category,tags) VALUES(%s,%s,%s,%s,%s)",
                  (st.session_state.user["user_id"],title.strip(),content.strip(),category.strip(),tags.strip()))
            st.session_state.page="Home"; st.rerun()

def post_view():
    pid=st.session_state.post_id; uid=st.session_state.user["user_id"]
    rows=query("SELECT p.*,u.name author FROM posts p JOIN users u ON p.user_id=u.user_id WHERE p.post_id=%s",(pid,),True)
    if not rows: st.warning("Post not found."); return
    p=rows[0]; st.title(p["title"]); st.caption(f"By {p['author']} · {p['created_at']}")
    st.write(p["content"])
    liked=query("SELECT like_id FROM likes WHERE user_id=%s AND post_id=%s",(uid,pid),True)
    saved=query("SELECT bookmark_id FROM bookmarks WHERE user_id=%s AND post_id=%s",(uid,pid),True)
    x,y=st.columns(2)
    count=query("SELECT COUNT(*) n FROM likes WHERE post_id=%s",(pid,),True)[0]["n"]
    if x.button(f"❤️ {'Unlike' if liked else 'Like'} ({count})"):
        if liked: query("DELETE FROM likes WHERE user_id=%s AND post_id=%s",(uid,pid))
        else: query("INSERT IGNORE INTO likes(user_id,post_id) VALUES(%s,%s)",(uid,pid))
        st.rerun()
    if y.button("Remove bookmark" if saved else "🔖 Bookmark"):
        if saved: query("DELETE FROM bookmarks WHERE user_id=%s AND post_id=%s",(uid,pid))
        else: query("INSERT IGNORE INTO bookmarks(user_id,post_id) VALUES(%s,%s)",(uid,pid))
        st.rerun()
    if p["user_id"]==uid:
        c,d=st.columns(2)
        if c.button("✏️ Edit"):
            st.session_state.edit_id=pid; st.session_state.page="Edit"; st.rerun()
        if d.button("🗑️ Delete"):
            st.session_state.confirm=True
    if st.session_state.user["role"]=="Admin" and st.button("Admin: delete post"):
        st.session_state.confirm=True
    if st.session_state.get("confirm"):
        st.warning("Delete this post and its comments?")
        c,d=st.columns(2)
        if c.button("Confirm delete"):
            query("DELETE FROM posts WHERE post_id=%s",(pid,)); st.session_state.confirm=False
            st.session_state.page="Home"; st.rerun()
        if d.button("Keep post"): st.session_state.confirm=False; st.rerun()
    st.divider(); st.subheader("💬 Comments")
    cms=query("""SELECT c.*,u.name author FROM comments c JOIN users u ON c.user_id=u.user_id
                 WHERE c.post_id=%s ORDER BY c.created_at""",(pid,),True)
    for cm in cms:
        with st.container(border=True):
            st.markdown(f"**{cm['author']}** · {cm['created_at']}")
            st.write(cm["comment"])
            if cm["user_id"]==uid or st.session_state.user["role"]=="Admin":
                if st.button("Delete comment",key=f"dc{cm['comment_id']}"):
                    query("DELETE FROM comments WHERE comment_id=%s",(cm["comment_id"],)); st.rerun()
    with st.form("comment",clear_on_submit=True):
        comment=st.text_area("Write a comment")
        ok=st.form_submit_button("Post comment")
    if ok:
        if comment.strip():
            query("INSERT INTO comments(post_id,user_id,comment) VALUES(%s,%s,%s)",(pid,uid,comment.strip())); st.rerun()
        else: st.warning("Comment cannot be empty.")

def profile():
    u=st.session_state.user
    pc=query("SELECT COUNT(*) n FROM posts WHERE user_id=%s",(u["user_id"],),True)[0]["n"]
    lc=query("SELECT COUNT(*) n FROM likes l JOIN posts p ON l.post_id=p.post_id WHERE p.user_id=%s",(u["user_id"],),True)[0]["n"]
    st.title("👤 Profile"); st.subheader(u["name"]); st.write(u["email"])
    a,b=st.columns(2); a.metric("Posts",pc); b.metric("Likes received",lc)

def admin():
    if st.session_state.user["role"]!="Admin": st.error("Admin access only."); return
    st.title("🛡️ Admin dashboard")
    us=query("SELECT user_id,name,email,role,created_at FROM users ORDER BY user_id",fetch=True)
    ps=query("SELECT p.post_id,p.title,u.name author,p.created_at FROM posts p JOIN users u ON p.user_id=u.user_id ORDER BY p.created_at DESC",fetch=True)
    a,b=st.columns(2); a.metric("Users",len(us)); b.metric("Posts",len(ps))
    st.subheader("Users"); st.dataframe(pd.DataFrame(us),use_container_width=True,hide_index=True)
    st.subheader("Manage posts")
    for p in ps:
        with st.container(border=True):
            st.write(f"**{p['title']}** — {p['author']}")
            if st.button("Delete",key=f"adm{p['post_id']}"):
                query("DELETE FROM posts WHERE post_id=%s",(p["post_id"],)); st.rerun()

def main():
    with st.sidebar:
        st.title("📝 BlogSphere")
        if st.session_state.user:
            st.write("Hello, "+st.session_state.user["name"])
            pages=["Home","Create Post","My Posts","Bookmarks","Profile"]
            if st.session_state.user["role"]=="Admin": pages.append("Admin")
            for p in pages:
                if st.button(p,use_container_width=True,type="primary" if st.session_state.page==p else "secondary"):
                    st.session_state.page=p; st.rerun()
            if st.button("Logout",use_container_width=True):
                st.session_state.user=None; st.session_state.page="Home"; st.rerun()
        else:
            for p in ["Home","Login","Register"]:
                if st.button(p,use_container_width=True,type="primary" if st.session_state.page==p else "secondary"):
                    st.session_state.page=p; st.rerun()
    page=st.session_state.page
    if page=="Home": home()
    elif page=="Login": login()
    elif page=="Register": register()
    elif page=="Post":
        if st.session_state.user: post_view()
        else: st.warning("Log in to interact with posts.")
    elif page=="Create Post":
        if st.session_state.user: editor()
        else: st.warning("Please log in first.")
    elif page=="Edit":
        edit=query("SELECT * FROM posts WHERE post_id=%s AND user_id=%s",(st.session_state.get("edit_id"),st.session_state.user["user_id"]),True)
        if edit: editor(edit[0])
        else: st.error("Post not found or not yours.")
    elif page=="My Posts":
        if st.session_state.user: st.title("📚 My Posts"); show_posts(posts(mine=True),)
        else: st.warning("Please log in.")
    elif page=="Bookmarks":
        if st.session_state.user: st.title("🔖 Bookmarks"); show_posts(posts(bookmarks=True))
        else: st.warning("Please log in.")
    elif page=="Profile":
        if st.session_state.user: profile()
        else: st.warning("Please log in.")
    elif page=="Admin": admin()

if __name__=="__main__": main()
