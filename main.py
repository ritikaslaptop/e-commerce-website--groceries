from flask import (Flask,
    render_template,
    g,
    request,
    redirect,
    session,
    url_for,
    send_from_directory,
    flash
    )
import mysql.connector
import os
import shutil
from werkzeug.utils import secure_filename


# app = Flask()
app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(32)
app.session_cookie_secure = True

mydb = mysql.connector.connect(
        host = "localhost",
        user = "ritika",
        password = "pass",
        )
mycursor = mydb.cursor()
mycursor.execute("SHOW databases")
databases = [x[0] for x in mycursor]

if "beamdb" not in databases:
    mycursor.execute("CREATE DATABASE beamdb")
    print("CREATED DATABASE beamdb")

    mycursor.execute("USE beamdb")
    print("USING DATABASE beamdb")

    mycursor.execute("CREATE TABLE customers (\
            username VARCHAR(255),\
            password VARCHAR(255)\
            )")
    print("CREATED TABLE customers")
    mycursor.execute("CREATE TABLE cart (\
            username VARCHAR(255),\
            product VARCHAR(255),\
            quantity int\
            )")
else:
    mycursor.execute("USE beamdb")
    print("USING DATABASE beamdb")

# User profiling
class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return f"<User: {self.username}>"

Users = []  #initialises Users list
# loading users into the list
def loadUsers():
    Users.clear()
    mycursor.execute("SELECT * FROM customers;")
    userdata = mycursor.fetchall()  #fetchall() is used to extract from select command
    for i in range(len(userdata)):
        Users.append(User(username=userdata[i][0], password=userdata[i][1]))    #Userclass object is being appended to User list
    print(f"Loaded users: {Users}")
loadUsers()

@app.before_request
def before_request():
    g.user = None
    if 'user_name' in session:
        user = [x for x in Users if x.username == session['user_name']]
        if user:
            user = user[0]
            g.user = user

# routes
# Log in
@app.route('/', methods=['GET','POST'])
def login():
    if g.user:
        print(f"{g.user} saved login cookie found")
        return redirect(url_for('products'))
    loadUsers()
    if request.method == 'POST' and request.form:
        session.pop('user_name', None)    # if 'user_name' is not found in session, pop() returns None to avoid error
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = [x for x in Users if x.username.lower() == username.lower()] # user is a Userclass object with the username that matches with entered username
        if user:    # this condition is to avoid error when no user matches with entered username
            user = user[0]
        if user and user.password == password:
            session['user_name'] = user.username
            print(f"User {user.username} *Has logged in.")
            return redirect(url_for('products'))
        else:
            print("Incorrect Username or Password")
    return render_template('login.html')

# create an account
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST' and request.form:
        newusername = request.form['newusername'].strip()
        newpassword = request.form['newpassword'].strip()

        ifuserexists = [x for x in Users if x.username.lower() == newusername.lower()]
        if ifuserexists:
            print(f"User {newusername} *Already exists")
            return redirect(url_for('login'))
        mycursor.execute(f"INSERT INTO customers (username, password) values ('{newusername}', '{newpassword}')")
        mydb.commit()
        print(f"New user {newusername} *Has been created and saved.")
        loadUsers()
        return redirect(url_for('login'))
    return render_template('signup.html')

# products page
prices = {"white sandwich bread":65, "chocolate chip muffins":125, "sliced loaf cake":150, "filtered milk":160, "white eggs (18x)":195, "cream cheese (8 oz.)":120}

@app.route('/products', methods=['GET', 'POST'])
def products():
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST' and request.form:
        product = request.form['addToCart']

        mycursor.execute(f"SELECT username FROM cart WHERE username='{g.user.username}' AND product='{product}';")
        sameuser = mycursor.fetchall()  #if the same product is added to cart, the quantity should be incremented
        if sameuser:
            mycursor.execute(f"UPDATE cart SET quantity=quantity+1 WHERE username='{sameuser[0][0]}' AND product='{product}'")
        else:
            mycursor.execute(f"INSERT INTO cart (username, product, quantity) values ('{g.user.username}', '{product}', 1)")

        mydb.commit()
        print(f"User {g.user.username} *Has added {product} to cart")
    return render_template('products.html')

# cart page
@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST' and request.form:
        increment = request.form.get('increment', False)
        if increment:
            mycursor.execute(f"UPDATE cart SET quantity=quantity+1 WHERE username='{g.user.username}' AND product='{increment}'")

        decrement = request.form.get('decrement', False)
        if decrement:
            mycursor.execute(f"SELECT quantity FROM cart WHERE username='{g.user.username}' AND product='{decrement}'")
            if mycursor.fetchall()[0][0] == 1:
                mycursor.execute(f"DELETE FROM cart WHERE username='{g.user.username}' AND product='{decrement}' ")
            else:
                mycursor.execute(f"UPDATE cart SET quantity=quantity-1 WHERE username='{g.user.username}' AND product='{decrement}'")

        delete = request.form.get('delete', False)
        if delete:
            mycursor.execute(f"DELETE FROM cart WHERE username='{g.user.username}' AND product='{delete}'")

        deleteCart = request.form.get('deleteCart', False)
        if deleteCart:
            mycursor.execute(f"DELETE FROM cart WHERE username='{g.user.username}'")
        mydb.commit()

        checkout = request.form.get('checkout', False)
        if checkout:
            print(checkout)
            mycursor.execute(f"DELETE FROM cart WHERE username='{g.user.username}'")
            return redirect(url_for('final'))

    mycursor.execute(f"SELECT product, quantity FROM cart WHERE username='{g.user.username}'")
    cartitems = mycursor.fetchall()
    cartlength = len(cartitems)

    totalprice = 0
    for i in range(cartlength):
        totalprice += cartitems[i][1]*prices[cartitems[i][0]]

    return render_template('cart.html', cartitems=cartitems, cartlength=cartlength, prices=prices, totalprice=totalprice)

# final page
@app.route('/final')
def final():
    if not g.user:
        return redirect(url_for('login'))
    return render_template('final.html')

# logout page
@app.route('/logout')
def logout():
    if g.user:
        print(f"User {g.user.username} *Has logged out.")
    session.pop('user_name', None)    # if 'user_name' is not found in session, pop() returns None to avoid error
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug='True')
