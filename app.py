from __future__ import print_function # In python 2.7
from flask import Flask, redirect, url_for, session, request, jsonify ,render_template
from flask_oauthlib.client import OAuth
#from flask_mysqldb import MySQL
from flaskext.mysql import MySQL
from base64 import b64encode
import json
import datetime
import smtplib
import sys
import config
import yaml

app = Flask(__name__)

db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
mysql = MySQL(app)


app.config['GOOGLE_ID'] = "948658928095-cjmtq3jeds1s2ccgt21dfb6lqrthrsbg.apps.googleusercontent.com"
app.config['GOOGLE_SECRET'] = "XJYg7VSkRLF3T47uoOYcC_2S"
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

google = oauth.remote_app(
    'google',
    consumer_key=app.config.get('GOOGLE_ID'),
    consumer_secret=app.config.get('GOOGLE_SECRET'),
    request_token_params={
        'scope': 'email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@app.route('/')
def first():
    session.pop('google_token' , None)
    return render_template('index.html')

@app.route('/google')
def index():
    if 'google_token' in session:
        me = google.get('userinfo')
        return jsonify({"data": me.data})
    return redirect(url_for('login'))


@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('google_token', None)
    session.pop('email' , None)
    return render_template('index.html')


@app.route('/login/authorized')
def authorized():
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['google_token'] = (resp['access_token'], '')
    me = google.get('userinfo')
    print('Hello world!\n\n', file=sys.stderr)
    email = me.data['email']
    verifiy = me.data['verified_email']
    session['email'] = email
    print(email)
    print(verifiy)
    print(type(email))
    #verify weather it is rvce email # ID
    if "rvce.edu.in" not in email:
        print("User Login not allowed")
    #check weatheer the user is new or world
    cur = mysql.connection.cursor()
    cur.execute("SELECT full_name FROM users WHERE email = %s",[email])
    name = cur.fetchone()
    print (name)
    if name == None :
        print ("new")
        return redirect('/newuser')
    else :
        print("OLD")
        return redirect('/dashboard')

    return redirect('/newuser')
    print("\n\n")
    return jsonify({"data": me.data})

@app.route('/newuser' , methods=['GET' , 'POST'])
def newuser():
    if request.method == 'POST' :
        userDetais = request.form
        name = userDetais['name']
        branch = userDetais['dept']
        email = session['email']
        cur = mysql.connection.cursor()
        print("name = %s , branch = %s \n" % (name , branch))
        cur.execute("INSERT INTO users(email , full_name , branch ) VALUES(%s , %s ,%s)" , (email , name , branch))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('dashboard'))
    return render_template('userDetails.html')

@app.route('/dashboard')
def dashboard():
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT branch FROM users WHERE email = %s " , [email] )
    branch = cur.fetchone();
    print("Dashboard")
    session['dept'] = branch[0]
    cur.execute("SELECT * FROM books WHERE branch = %s " , [branch[0]] )
    display = cur.fetchall()
    #print(display)
    return render_template('dashboard.html' )


@app.route('/profile')
def profile():
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT branch FROM users WHERE email = %s " , [email] )
    branch = cur.fetchone();
    session['dept'] = branch[0]
    cur.execute("SELECT * FROM users WHERE email = %s " , [email] )
    display = cur.fetchall()
    #print(display)
    jsondata = jsonify(display)
    #return jsondata
    return render_template('profile.html' , dis = display )

@app.route('/profile/edit' , methods=['GET' , 'POST'])
def editDetails():
    cur = mysql.connection.cursor()
    if request.method == 'POST' :
        editDetails = request.form
        try:
            edit = editDetails['edit']
            print(edit)
            cur.execute("SELECT * FROM books WHERE book_id = %s AND status = 'available' " , [edit] )
            bookDetails = cur.fetchone();
            print("HERE")
            return render_template('editBookDetails.html' , b = bookDetails)
        except:
            try:
                bookIdForDelete = editDetails['updateData']
                title  = editDetails['title']
                author = editDetails['author']
                edition = editDetails['edition']
                price = editDetails['price']
                id = editDetails['bookid']
                rating = editDetails['rating']
                branch = editDetails['dept']
                sem = editDetails['sem']
                print(author+" "+id)
                cur.execute("UPDATE books SET title = %s , author = %s , edition = %s , price = %s , rating = %s ,sem = %s WHERE book_id = %s " ,[title , author , edition , price , rating , sem , id])
                mysql.connection.commit()
                return 'Updated Sucessfully'
            except:
                deleteId = editDetails['delete']
                cur.execute("DELETE FROM books WHERE book_id = %s " , [deleteId])
                #mysql.connection.commit()
                return deleteId

@app.route('/profile/purchased')
def pruchased():

        email = session['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM sold , books  WHERE sold.buyer = %s AND sold.status = 'sold' AND books.status = 'sold'",[email])
        booksList = cur.fetchall()
        print(booksList)
        return render_template('addreview.html' , booksList = booksList)


@app.route('/profile/purchased/addreview' ,methods = ['GET' , 'POST'])
def addreview():
    if request.method == 'POST' :
        reviewForm = request.form
        bookid = reviewForm['addpublicreview']
        bookreview= reviewForm['publicreview']
        email = session['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT title , author FROM books WHERE book_id = %s ", [bookid])
        bookDetails = cur.fetchone()
        title = bookDetails[0]
        author = bookDetails[1]
        cur.execute("INSERT INTO reviews (title , author , reviewby  , comments) VALUES (%s ,%s , %s , %s )  " , [title , author  ,email , bookreview])
        mysql.connection.commit()
        print(bookid)
        print(bookreview)
        return render_template('addreview.html')
    return  "NOT POST"



@app.route('/profile/uploaded')
def uploaded():
    try:
        email = session['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM books WHERE uploader = %s AND status = 'available'",[email])
        booksList = cur.fetchall()
        return render_template('listOfMyBooks.html' , booksList = booksList)

    except :
        return redirect(url_for('logout'))
    #email = session['email']
    #cur = mysql.connection.cursor()

@app.route('/profile/pending')
def pending():
    try:
        cur = mysql.connection.cursor()
        email = session['email']
        #cur.execute("SELECT * FROM books WHERE status = 'booked' AND uploader = %s " , [email])
        #notifications = cur.fetchall()
        #cur.execute("SELECT buyer FROM sold WHERE status = 'booked' AND seller = %s " , [email])
        #buyerInfo = cur.execute()
        cur.execute("SELECT  * FROM books INNER JOIN sold ON books.uploader=sold.seller WHERE books.status = 'booked' AND books.book_id = sold.book_id AND books.uploader = %s ",[email])
        notifiy = cur.fetchall()
        return render_template('notifiy.html' ,  notifiy =notifiy )
    except :
            return redirect(url_for('logout'))

@app.route('/profile/sold')
def sold():
    #try:
        email = session['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM sold WHERE seller  = %s AND status = 'sold'",[email])
        booksList = cur.fetchall()
        return render_template('listOfMyBooks.html' , booksList = booksList)

@app.route('/profile/requested')
def reqquested():
    #try:
        email = session['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM sold WHERE buyer = %s AND status = 'booked'",[email])
        booksList = cur.fetchall()
        return render_template('listOfMyBooks.html' , booksList = booksList)
    #except :
    #    return redirect(url_for('logout'))

@app.route('/bookDetails', methods=['GET' , 'POST'])
def owner():
        print('Book Details  \n')
        bookname = request.args.get('book')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM books WHERE title = %s ", [bookname])
        bookDetails = cur.fetchone()
        cur.execute("SELECT uploader , price , book_id FROM books WHERE title = %s AND status = 'available' ORDER BY price ASC" , [bookname])
        bookSellers = cur.fetchall()
        image = bookDetails[12]
        cur.execute("SELECT * FROM reviews WHERE title = %s ", [bookname])
        reviews = cur.fetchall()
        return render_template('bookSellers.html' , display = bookDetails , seller = bookSellers , reviews = reviews )
    #return '\nBook Details'


@app.route('/requestBook' , methods=['GET' , 'POST'])

def requestBook():
    if request.method  == 'POST' :
        ownerForm = request.form
        req = ownerForm['req']
        cur = mysql.connection.cursor()

        cur.execute("SELECT status FROM books WHERE book_id = %s " ,[req])
        status = cur.fetchone()
        print("status " +status[0])

        if status[0] != 'available':
            return 'SORRY THIS BOOK HAS BEEN BOOKED BUY SOME ONE ELSE'
        else:
            #all details of the user who requested the book
            try:
                reqEmail = session['email']
                cur.execute("SELECT * FROM users WHERE email = %s " , [reqEmail])
                dbObject = cur.fetchone()
                reqName  = dbObject[2]
                reqPhone = dbObject[5]
                server = smtplib.SMTP('smtp.gmail.com:587')
                server.ehlo()
                server.starttls()
                server.login(config.EMAIL , config.PASS)

                #book Details
                cur.execute("SELECT * FROM books WHERE book_id = %s " ,[req])
                dbObject = cur.fetchone()
                bookTitle = dbObject[1]
                bookAuthor = dbObject[2]
                bookEdition = dbObject[3]
                ownerEmail = dbObject[5]
                price = dbObject[4]
                #owner Details
                cur.execute("SELECT * FROM users WHERE email = %s " ,[ownerEmail])
                dbObject = cur.fetchone()
                ownerName = dbObject[2]
                ownerPhone = dbObject[5]

                cur.execute("SELECT * FROM users WHERE email = %s " ,[ownerEmail])
                dbObject = cur.fetchone()
                ownerName = dbObject[2]
                ownerPhone = dbObject[5]


                now = datetime.datetime.now()
                year = (now.year)
                month = (now.month)
                day = (now.day)
                #tdate = f"{year}-{month}-{day}"
                tdate = "12-12-2018"
                print(tdate)
                try:
                    cur.execute("UPDATE books SET status = 'booked' WHERE book_id = %s " , [req] )
                    cur.execute("INSERT INTO `sold` (`book_id`, `buyer`, `seller`, `status`, `date`) VALUES (%s, %s, %s, 'booked', %s)",(req,reqEmail,ownerEmail , tdate))
                    mysql.connection.commit()
                    try:
                        #server = smtplib.SMTP('smtp.gmail.com:587')
                        #server.ehlo()
                        #server.starttls()
                        #server.login(config.EMAIL , config.PASS)
                        subject = "Notification For Book Request"
                        msg = f"Hello ! The user with email id : {reqEmail} has requested you the book Titled = {bookTitle}\nAuthor = {bookAuthor}\nEdition = {bookEdition} \npriced :{price} \nThe Student Details are \nName = {reqName}\nPhone = {reqPhone} "
                        message = 'Subject:{}\n\n{}'.format(subject , msg)
                        server.sendmail(config.EMAIL , ownerEmail , message)
                        msg = f"Hello ! Your request has been sent to the owner of the book \nTitled = {bookTitle}\nAuthor = {bookAuthor}\nEdition = {bookEdition} \npriced :{price} \nThe Details of book owner are \nName = {ownerName}\nPhone = {ownerPhone} \nEmail = {ownerEmail}"
                        subject = "Conformation For Your Book Request"
                        message = 'Subject:{}\n\n{}'.format(subject , msg)
                        server.sendmail(config.EMAIL , reqEmail , message)
                        print("sent")
                        server.quit()
                    except:
                        return 'email not sent !'
                    return 'Email notification has been sent to the user'
                except:
                    return 'Failed'
            except:
                return 'Login first'
            #print(cur.fetchone())
    return ' hmmmm Your request has been sent to the seller :)'

@app.route('/search', methods=['GET' , 'POST'])
def search():
    i = 0
    print("something")

    if i == 0:
        i = i + 1
        return render_template('search.html')
    else:
        return '<h1> hello </h1> hello'


@app.route('/notifiy')
def notify():
    #check if logged in or not
    if session['email'] is None :
        session.pop('google_token', None)
        return render_template('index.html')

    cur = mysql.connection.cursor()
    email = session['email']
    #cur.execute("SELECT * FROM books WHERE status = 'booked' AND uploader = %s " , [email])
    #notifications = cur.fetchall()
    #cur.execute("SELECT buyer FROM sold WHERE status = 'booked' AND seller = %s " , [email])
    #buyerInfo = cur.execute()
    cur.execute("SELECT  * FROM books INNER JOIN sold ON books.uploader=sold.seller WHERE books.status = 'booked' AND books.book_id = sold.book_id AND books.uploader = %s ",[email])
    notifiy = cur.fetchall()

    emailList = list(notifiy)
    nameList = []
    for i in notifiy:
        cur.execute("SELECT full_name FROM users WHERE email = %s " , [i[13]])
        nameList.append(cur.fetchone())
    for i in range(len(nameList)):
        print(emailList[i][13])
        print(nameList[i])
    return render_template('notifiy.html' ,  notifiy = tuple(emailList) , nm = nameList  )#, buyerInfo = buyerInfo)


@app.route('/asd')
def asd():
    try:
        email = session['email']
        if email is None :
            return 'Login Please'
        else :
            cur = mysql.connection.cursor()
            cur.execute("SELECT branch FROM users WHERE email = %s " , [email] )
            branch = cur.fetchone();
            #print("Dashboard")
            session['dept'] = branch[0]
            cur.execute("SELECT DISTINCT book_id ,title ,author ,price,  rating , branch ,rating  FROM books WHERE branch = %s " , [branch[0]] )
            display = cur.fetchall()
            cur.execute("SELECT * FROM books WHERE status = 'booked' AND uploader = %s " , [email])
            notifications = cur.fetchall()
            #print(display)
            return render_template('dashboards.html' , userDetails = display , notif = notifications)
    except:
        return "Log in please"

@app.route('/closeDeal', methods=['GET', 'POST'])
def closeDeal():
    if request.method == 'POST' :
        bookDetaisForm = request.form
        bookid = bookDetaisForm['deal']
        print(bookid)
        cur = mysql.connection.cursor()
        updateQuery = f"UPDATE books SET status = 'sold' WHERE book_id = {bookid}"
        updateQuery2 = f"UPDATE sold SET status = 'sold' WHERE book_id = {bookid}"
        cur.execute(updateQuery)
        cur.execute(updateQuery2)
        #mysql.connection.commit()
        cur.execute("SELECT * FROM sold WHERE book_id = '6'")
        json = jsonify(cur.fetchone())
        return render_template( 'ownerDetails.html' ,js = json)
        #cur.close()
        #return bookid


@app.route('/sell',methods=['GET' , 'POST'])
def sell():
        if request.method == 'POST' :
            userDetais = request.form
            title  = userDetais['title']
            author = userDetais['author']
            price = userDetais['price']
            uploader = session['email']
            rating = userDetais['rating']
            branch = userDetais['dept']
            sem = userDetais['sem']
            photo = userDetais['pic']
            #return title + sem + branch
            #email = userDetais['email']
            if title == "" or author == "" or price == "" or uploader == "" or branch == "" or sem == "" :
                return 'Please Enter All the values'
            cur  = mysql.connection.cursor()
            cur.execute("INSERT INTO books(title , author , price , uploader , rating , branch , sem ,status ,photo ) VALUES(%s , %s , %s , %s , %s , %s ,%s  ,'available' , %s)" , (title , author , price , uploader , rating , branch , sem ,photo ))
            mysql.connection.commit()
            cur.close()
            return 'done'
        return render_template('sell.html')

@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


if __name__ == '__main__':
    app.run()
