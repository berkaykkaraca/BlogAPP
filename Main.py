from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, TextAreaField, StringField, PasswordField, validators, IntegerField
from functools import wraps
from passlib.hash import sha256_crypt
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
from flaskext.noextref import NoExtRef

app = Flask(__name__)
noext = NoExtRef(app)
app.secret_key = "bkk"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "educationBlog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)
tempcode = random.randint(100000,999999)
tempbool = False
debug = dict()
debug["session"]="None"
adminusername = "bkk_root"
adminpassword="bkkadmin"
tempdict = {
    "type":"None"
}
"""------------------------------FORM CLASSES---------------------------------------"""

class RegisterForm(Form):
    name = StringField("Name and Surname:", validators=[
                       validators.length(min=4, max=25),validators.DataRequired()])
    username = StringField("Username:", validators=[validators.length(
        min=5, max=35), validators.DataRequired(message="Lütfen bir kullanıcı adı belirleyin")])
    email = StringField("Email:", validators=[validators.Email(
        message="Please Enter a Valid Email."), validators.DataRequired(message="Lütfen bir email adresi belirleyin")])
    password = PasswordField("Password:", validators=[
        validators.length(min=7, max=35),
        validators.EqualTo("confirm", message="Parolanız uyuşmuyor."),
        validators.DataRequired(message="Lütfen bir şifre belirleyin.")

    ])
    confirm = PasswordField("Confirm Password:",validators=[validators.DataRequired()])


class LoginForm(Form):
    username = StringField("Username:")
    password = PasswordField("Password:")




class ArticleForm(Form):
    title = StringField("Title:", validators=[
                        validators.length(min=5, max=200)])
    category = StringField("Category:", validators=[
                        validators.length(max=40)])
    content = TextAreaField("Content:", validators=[validators.length(min=10)])


class QuestionForm(Form):
    title = StringField("Title:", validators=[validators.DataRequired()])
    question = TextAreaField("Question:", validators=[
                             validators.DataRequired()])


class AnswerForm(Form):
    answer = TextAreaField("", validators=[validators.DataRequired()], render_kw={
                           "placeholder": 'Enter your answer here'})


class PasswordForm(Form):
    email = StringField("Email:", validators=[validators.Email(
        message="Please Enter a Valid Email."), validators.DataRequired(message="Lütfen bir email adresi belirleyin")])


class ResetPasswordForm(Form):
    code = StringField("Code")


class ChangePasswordForm(Form):
    password = PasswordField("Password:", validators=[
        validators.length(min=7, max=35),
        validators.EqualTo("confirm", message="Parolanız uyuşmuyor."),
        validators.DataRequired(message="Lütfen bir şifre belirleyin.")

    ])
    confirm = PasswordField("Confirm Password:")
"""-------------------------------------------------------------------------------------"""


"""------------------------------DECORATORS---------------------------------------"""

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Lütfen giriş yapınız...", "danger")
            return redirect(url_for("teacherLogin"))
    return decorated_function


def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session["type"] == "teacher":
            return f(*args, **kwargs)
        else:
            flash("Please Login as a Teacher...", "danger")
            return redirect(url_for("index"))
    return decorated_function
def admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session["type"] == "admin":
            return f(*args, **kwargs)
        else:
            flash("Please Login as a Admin...", "danger")
            return redirect(url_for("index"))
    return decorated_function


"""-------------------------------------------------------------------------------------"""



@app.route("/")
def index():

    return render_template("index.html")
@app.route("/login")
def login():
    return render_template("login.html")
@app.route("/logout")
def logout():
    session["logged_in"] = False
    session["type"] = "None"
    session.clear()
    return redirect(url_for("index"))

@app.route("/settings/<string:username>/account")
def settings(username):
    return render_template("settings/account.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(s, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")


"""------------------------------------STUDENT-------------------------------------------------"""

@app.route("/student/register", methods=["GET", "POST"])
def studentRegister():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        try:
            s = "INSERT INTO student(name,username,email,password,type) VALUES(%s,%s,%s,%s,'student')"
            cursor.execute(s, (name, username, email, password))
            mysql.connection.commit()
        except mysql.connection.IntegrityError as err:
            flash("This username has taken.", "danger")
            return redirect(url_for("studentRegister"))

        cursor.close()
        flash("Başarıyla Kayıt oldunuz.", "success")
        return redirect(url_for("studentLogin"))
    else:
        return render_template("/student/register.html", form=form)


@app.route("/student/login", methods=["GET", "POST"])
def studentLogin():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        s = "SELECT * FROM student WHERE username=%s;"
        result = cursor.execute(s, (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password, real_password):
                flash("You LoggedIn Successfully", "success")
                session["logged_in"] = True
                session["username"] = username
                session["type"] = "student"
                return redirect(url_for("index"))
            else:
                flash("Wrong Password...", "danger")
                return redirect(url_for("studentLogin"))
        else:
            flash("Wrong Username...", "danger")
            return redirect(url_for("studentLogin"))
    return render_template('/student/login.html', form=form)
"""-------------------------------------------------------------------------------------"""




"""------------------------------------TEACHER-------------------------------------------------"""

@app.route("/teacher/register", methods=["GET", "POST"])
def teacherRegister():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        try:
            cursor = mysql.connection.cursor()
            s = "INSERT INTO teacher(name,username,email,password,type) VALUES(%s,%s,%s,%s,'teacher')"
            cursor.execute(s, (name, username, email, password))
            mysql.connection.commit()
        except mysql.connection.IntegrityError as err:
            flash("This username has taken.", "danger")
            return redirect(url_for("teacherRegister"))
        cursor.close()
        flash("You Registered Successfully", "success")
        return redirect(url_for("teacherLogin"))
    else:
        return render_template("/teacher/register.html", form=form)


@app.route("/teacher/login", methods=["GET", "POST"])
def teacherLogin():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data
        a = False
        if username == adminusername and password == adminpassword:
            session["type"]="admin"
            a = True
        cursor = mysql.connection.cursor()
        s = "SELECT * FROM teacher WHERE username=%s;"
        result = cursor.execute(s, (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password, real_password):
                flash("You LoggedIn Successfully.", "success")
                session["logged_in"] = True
                session["username"] = username
                if a == False:
                    session["type"] = "teacher"
                return redirect(url_for("index"))
            else:
                flash("Wrong Password", "danger")
                return redirect(url_for("teacherLogin"))
        else:
            flash("Wrong Username...", "danger")
            return redirect(url_for("teacherLogin"))
    return render_template('/teacher/login.html', form=form)
"""-------------------------------------------------------------------------------------"""



"""------------------------------------ARTİCLE-------------------------------------------------"""


@app.route("/addarticle", methods=["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        category = form.category.data
        content = form.content.data
        author = session['username']
        sql = "INSERT INTO articles(title,category,author,content) VALUES (%s,%s,%s,%s)"
        cur = mysql.connection.cursor()
        cur.execute(sql, (title,category, author, content))
        mysql.connection.commit()
        cur.close()
        flash("New Article Added Successfully.", "info")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form=form)


@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles WHERE id=%s"
    result = cursor.execute(s, (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article=article)
    else:
        return render_template("article.html")


@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles WHERE author = %s AND id = %s"
    result = cursor.execute(s, [session["username"], id])
    if result > 0:
        s2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(s2, (id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Such an article does not exist or you do not have authority.", "danger")
        return redirect(url_for("index"))


@app.route("/update/<string:id>", methods=["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        s1 = "SELECT * FROM articles WHERE id=%s AND author=%s;"
        result = cursor.execute(s1, (id, session["username"]))
        if result == 0:
            flash("Such an article does not exist or you do not have authority.", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form=form)

    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        s = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(s, (newTitle, newContent, id))
        mysql.connection.commit()
        flash("Article Updated Successfully", "success")
        return redirect(url_for("dashboard"))


@app.route("/articles")
def articles():
    a=True
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles"
    s2= "SELECT COUNT(id) AS num,category FROM articles GROUP BY category"
    s3 = "SELECT COUNT(id) AS 'all' FROM articles"
    result2 = cursor.execute(s2)
    categories = cursor.fetchall()
    result3 = cursor.execute(s3)
    all = cursor.fetchone()
    result = cursor.execute(s)
    if result > 0:
        
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles,categories=categories,a=a,all=all)
    else:
        return render_template("articles.html")
    

@app.route("/articles/desc")
def articlesOrderdesc():
    a = True
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles ORDER BY created_date DESC"
    s2= "SELECT COUNT(id) AS num,category FROM articles GROUP BY category"
    result2 = cursor.execute(s2)
    categories = cursor.fetchall()
    result = cursor.execute(s)
    if result > 0:
        
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles,categories=categories,a=a)
    else:
        return render_template("articles.html")
@app.route("/articles/asc")
def articlesOrderasc():
    a=True
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles ORDER BY created_date ASC"
    s2= "SELECT COUNT(id) AS num,category FROM articles GROUP BY category"
    result2 = cursor.execute(s2)
    categories = cursor.fetchall()
    result = cursor.execute(s)
    if result > 0:
        
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles,categories=categories,a=a)
    else:
        return render_template("articles.html")

@app.route("/articlesGroup/<string:category>")
def articlesGroup(category):
    a = False
    cursor = mysql.connection.cursor()
    s2= "SELECT COUNT(id) AS num,category FROM articles GROUP BY category"
    result2 = cursor.execute(s2)
    categories = cursor.fetchall()
    s = "SELECT * FROM articles WHERE category = %s"
    result = cursor.execute(s,(category,))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles,categories=categories,a=a)
    else:
        return render_template("articles.html")

@app.route("/articles/category")
def articlescat():
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM articles GROUP BY category"
    result = cursor.execute(s)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")
    
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sql = "select * from articles where title like '%" + \
            str(keyword) + "%' "
        result = cursor.execute(sql)
        if (result == 0):
            flash("Such an article does not exist.", "danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            s2= "SELECT COUNT(id) AS num,category FROM articles GROUP BY category"
    
            result2 = cursor.execute(s2)
            categories = cursor.fetchall()
            return render_template("articles.html", articles=articles, categories=categories)
"""-------------------------------------------------------------------------------------"""




"""-------------------------------------QUESTİONS AND ANSWERS------------------------------------------------"""

@app.route("/askquestion", methods=["GET", "POST"])
@login_required
@teacher_required
def askQuestion():
    form = QuestionForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        question = form.question.data
        author = session["username"]
        sql = "INSERT INTO questions(author,title,question) VALUES (%s,%s,%s)"
        cur = mysql.connection.cursor()
        cur.execute(sql, (author, title, question))
        mysql.connection.commit()
        cur.close()
        flash("New Question Added Successfully", "info")
        return redirect(url_for("questions"))
    return render_template("askquestion.html", form=form)


@app.route("/questions")
def questions():
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM questions"
    result = cursor.execute(s)
    if result > 0:
        questions = cursor.fetchall()
        return render_template("questions.html", questions=questions)
    else:
        return render_template("questions.html")


@app.route("/question/<string:id>")
def question(id):
    cursor = mysql.connection.cursor()
    cursor2 = mysql.connection.cursor()

    s = "SELECT * FROM questions WHERE question_id=%s"
    result = cursor.execute(s, (id,))
    s2 = "SELECT * FROM answers WHERE question_id=%s"
    result2 = cursor2.execute(s2, (id,))

    if result > 0:
        answers = cursor2.fetchall()
        question = cursor.fetchone()
        return render_template("question.html", question=question, answers=answers)
    else:
        return render_template("question.html")


@app.route("/answer/<string:id>", methods=["GET", "POST"])
@login_required
def answer(id):
    
    form = AnswerForm(request.form)
    cur2 = mysql.connection.cursor()
    s = "SELECT * FROM questions WHERE question_id = %s"
    result1 = cur2.execute(s, (id,))
    q = cur2.fetchone()
    if request.method == "POST" and form.validate():
        author = session['username']
        answer = form.answer.data
        question_id = id

        sql = "INSERT INTO answers(author,answer,question_id) VALUES (%s,%s,%s)"
        cur = mysql.connection.cursor()
        cur.execute(sql, (author, answer, question_id))
        mysql.connection.commit()
        cur.close()
        flash("Your Answer Added Successfully.", "info")
        return redirect(url_for("questions"))
    return render_template("answer.html", form=form, q=q)


@app.route("/searchquestion", methods=["GET", "POST"])
def searchQuestion():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sql = "select * from questions where title like '%" + \
            str(keyword) + "%' "
        result = cursor.execute(sql)
        if (result == 0):
            flash("Such an question does not exist.", "danger")
            return redirect(url_for("questions"))
        else:
            questions = cursor.fetchall()
            return render_template("questions.html", questions=questions)

"""-------------------------------------------------------------------------------------"""
"""-------------------------------------PASSWORD------------------------------------------------"""

@app.route("/forgotpassword", methods=["GET", "POST"])
def forgotPassword():
    form = PasswordForm(request.form)
    if request.method == "POST":
        cur = mysql.connection.cursor()
        s = "SELECT email FROM student WHERE email =%s"
        email1 = form.email.data
        result = cur.execute(s, (email1,))

        if result > 0:
            email = cur.fetchone()
            sendMail(email1)
            debug["session"]=email1
            return redirect(url_for("resetPassword", email=email1))
            
        else:
            flash("Wrong Email..", "danger")
            return redirect(url_for("forgotPassword"))
    else:
        return render_template("/student/forgotpassword.html", form=form)


@app.route("/resetpassword/<email>", methods=["GET", "POST"])
def resetPassword(email):
    global tempcode
    
    form = ResetPasswordForm(request.form)
    if debug["session"]!=email:
        flash("No auth","danger")
        return redirect(url_for("forgotPassword"))
    if request.method == "POST":
        submitted_code = form.code.data
        code = tempcode
        if str(submitted_code) == str(code):
            tempcode = 0
            return redirect(url_for("changePassword", email=email))
        else:
            flash("Kod yanlış", "danger")
            return redirect(url_for("resetPassword", email=email))

    else:
        return render_template("/student/resetpassword.html", email=email, form=form)


@app.route("/changepassword/<email>", methods=["GET", "POST"])

def changePassword(email):
    form = ChangePasswordForm(request.form)
    if request.method == "POST" and form.validate() :
        cur = mysql.connection.cursor()
        password = sha256_crypt.encrypt(form.password.data)
        s = "UPDATE student SET password = %s WHERE email=%s"
        result = cur.execute(s, (password, email))
        mysql.connection.commit()
        flash("Your password successfully changed","success")
        return redirect(url_for("studentLogin"))
    else:
        return render_template("/student/changepassword.html", form=form)
    
    




@app.route("/forgotpasswordteacher", methods=["GET", "POST"])
def forgotPasswordTeacher():
    form = PasswordForm(request.form)
    if request.method == "POST":
        cur = mysql.connection.cursor()
        s = "SELECT email FROM student WHERE email =%s"
        email1 = form.email.data
        result = cur.execute(s, (email1,))

        if result > 0:
            email = cur.fetchone()
            sendMail(email1)
            return redirect(url_for("resetPasswordTeacher", email=email1))
        else:
            flash("Wrong Email..", "danger")
            return redirect(url_for("forgotPasswordTeacher"))
    else:
        return render_template("/student/forgotpassword.html", form=form)


@app.route("/resetpasswordteacher/<email>", methods=["GET", "POST"])
def resetPasswordTeacher(email):
    global tempcode
    form = ResetPasswordForm(request.form)
    if request.method == "POST":
        submitted_code = form.code.data
        code = tempcode
        if str(submitted_code) == str(code):
            tempcode = 0
           
            return redirect(url_for("changePasswordTeacher", email=email))
        else:
            flash("Kod yanlış", "danger")
            return redirect(url_for("resetPasswordTeacher", email=email))

    else:
        return render_template("/student/resetpassword.html", email=email, form=form)


@app.route("/changepasswordteacher/<email>", methods=["GET", "POST"])

def changePasswordTeacher(email):
    form = ChangePasswordForm(request.form)
    if request.method == "POST" and form.validate() :
        cur = mysql.connection.cursor()
        password = sha256_crypt.encrypt(form.password.data)
        s = "UPDATE teacher SET password = %s WHERE email=%s"
        result = cur.execute(s, (password, email))
        mysql.connection.commit()
        flash("Your password successfully changed","success")
        return redirect(url_for("teacherLogin"))
    else:
        return render_template("/student/changepassword.html", form=form)

@app.route("/settings/<username>/deleteaccount",methods=["GET","POST"])
@login_required
def deletaccount(username):
    form = ChangePasswordForm(request.form)
    if request.method == "POST" and form.validate() :
        cur = mysql.connection.cursor()
        password = sha256_crypt.encrypt(form.password.data)
        if session["type"] == "teacher":
            s = "DELETE FROM teacher WHERE username = %s"
        else:
            s = "DELETE FROM student WHERE username = %s"
        s2 = "DELETE FROM articles WHERE author = %s"
        result = cur.execute(s,(username,))
        result2 = cur.execute(s2,(username,))
        session["logged_in"] = False
        session["type"] = "None"
        session.clear()
        mysql.connection.commit()
        flash("Account deleted!","info")
        return redirect(url_for('index'))
    else:
        return render_template("/settings/deleteaccount.html",form = form)
       

def sendMail(email):
    global tempcode
    message = MIMEMultipart()
    code = random.randint(100000, 999999)
    tempcode = code
    rand = str(code)
    message["From"] = "sender_email@gmail.com"
    message["To"] = "receiver_email@gmail.com"
    message["Subject"] = " Mail Gönderme"

    yazi = rand

    g = MIMEText(yazi, "plain")
    message.attach(g)
    try:
        mail = smtplib.SMTP('smtp.outlook.com', 587)
        mail.ehlo()
        mail.starttls()
        mail.login("sender_email@gmail.com", "sender_email@gmail.com")
        mail.sendmail(message["From"], message["To"], message.as_string())
        print("Mail gönderildi..")
        mail.quit()
    except Exception:
        sys.stderr.write("ERROR")
        sys.stderr.flush()
"""-------------------------------------------------------------------------------------"""
"""-------------------------------------Admin Pages------------------------------------------------"""

@app.route("/admin/users/teachers")
@admin
def teachers():
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM student"
    s2 = "Select*FROM teacher"
    result2=cursor.execute(s2)
    teachers=cursor.fetchall()
    result = cursor.execute(s)
    
    students = cursor.fetchall()
    return render_template("/admin/teachers.html", students=students,teachers=teachers)
    
@app.route("/admin/users/students")
@admin
def students():
    cursor = mysql.connection.cursor()
    s = "SELECT * FROM student"
    s2 = "Select*FROM teacher"
    result = cursor.execute(s)
    students=cursor.fetchall()
    
    return render_template("/admin/students.html", students=students)
@app.route("/admin/delete/teacher/<string:username>")
def deleteTeacher(username):
    cursor = mysql.connection.cursor()
    query = "DELETE FROM teacher WHERE username=%s"
    cursor.execute(query, (username,))
    mysql.connection.commit()

    s = "DELETE FROM articles WHERE author=%s",
    cursor.execute(s,(username,))
    mysql.connection.commit()
    flash('Teacher object has been deleted.','success')
    return redirect(url_for('teachers'))


@app.route("/admin/delete/student/<string:username>")
def deleteStudent(username):
    cursor = mysql.connection.cursor()
    sql = "SELECT*FROM student WHERE username = %s"
    
    result = cursor.execute(sql,(username,))
    if result>0:
        query = "DELETE FROM student WHERE username=%s"
        r2=cursor.execute(query, (username,))
        s = "SELECT*FROM articles WHERE author=%s"
        r1 =cursor.execute(s,(username,))
        if r1>0:
            query1 = "DELETE FROM articles WHERE author=%s"
            cursor.execute(query1,(username,))
            mysql.connection.commit()
            flash("Successfully Deleted Student","success")
            return redirect(url_for("students"))
        
        mysql.connection.commit()
        flash('Student object has been deleted.','success')
        return redirect(url_for('students'))
    else:
        return redirect(url_for("students"))
    
if __name__ == "__main__":

    app.run(debug=True)


