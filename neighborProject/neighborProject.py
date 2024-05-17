from flask import Flask, render_template, request, flash, url_for, session, redirect
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key ='duracell'

DB_HOST = "localhost"
DB_NAME = "project1"
DB_USER = "postgres"
DB_PASS = "1107"

conn = psycopg2.connect(dbname = DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

# /ROOT
@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# /Vote
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        # SHOW ALL neighborhoods
        cursor.execute("""SELECT * FROM application a 
                          JOIN Users u ON a.applicant_id = u.user_id
                          JOIN blocks b ON a.block_id = b.block_id""")
        applications = cursor.fetchall()
        current_vote = 0
        
        # Handle votes
        if request.method == 'POST':
            form_id = request.form.get('form_id')
            
            if form_id == 'form1':
                application_id = request.form.get('application_id')
                
                # Fetch block_id of the application
                cursor.execute("""SELECT block_id FROM Application WHERE application_id = %s;""", 
                               (application_id,))
                application = cursor.fetchone()
                application_block_id = application['block_id']
                
                # Check if the voter is a member of the same block
                cursor.execute("""SELECT * FROM Block_Memberships 
                                  WHERE block_id = %s AND user_id = %s AND status = 'active';""", 
                               (application_block_id, session['user_id']))
                membership = cursor.fetchone()
                
                if not membership:
                    flash('You are not a member of this block and cannot vote on this application.')
                else:
                    cursor.execute("""SELECT * FROM Votes 
                                      WHERE application_id = %s AND voter_id = %s;""", 
                                   (application_id, session['user_id']))
                    existing_vote = cursor.fetchone()
                    
                    if existing_vote:
                        flash('You can only vote once for a particular application.')
                    else:
                        cursor.execute("""SELECT SUM(CAST(vote_count AS INTEGER)) AS total_votes
                                          FROM Votes
                                          WHERE application_id = %s;""", (application_id,))
                        current_vote_result = cursor.fetchone()
                        current_vote = current_vote_result['total_votes'] if current_vote_result['total_votes'] else 0

                        # Insert new vote
                        cursor.execute("""INSERT INTO Votes (application_id, voter_id, vote_count, created_at, updated_at)
                                          VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);""", 
                                       (application_id, session['user_id'], current_vote + 1))

                        # CHECK VOTE AGAIN
                        cursor.execute("""SELECT SUM(CAST(vote_count AS INTEGER)) AS total_votes
                                          FROM Votes
                                          WHERE application_id = %s;""", (application_id,))
                        current_vote_result = cursor.fetchone()
                        new_vote = current_vote_result['total_votes'] if current_vote_result['total_votes'] else 0

                        if new_vote >= 3:
                            cursor.execute("""UPDATE Application
                                              SET status = 'approved'
                                              WHERE application_id = %s;""", (application_id,))
                            # Become a member of that block
                            cursor.execute("""INSERT INTO Block_Memberships (block_id, user_id, status, join_date, update_date)
                                              VALUES (%s, %s, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);""",
                                           (application_block_id, session['user_id']))

                        flash('Thank you for your vote')

        return render_template('vote.html', applications=applications)
    return redirect(url_for('login'))



# /Applications
@app.route('/applications', methods=['GET', 'POST'])
def applications():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    see_blocks = False
    blocks = []  # Initialize blocks as an empty list
    your_app = []  # Initialize your_app as an empty list
    if 'loggedin' in session:
        # SHOW ALL neighborhoods
        cursor.execute("""SELECT * FROM neighborhoods""")
        neighborhoods = cursor.fetchall()
    
        # SEE BLOCKS
        if request.method == 'POST':
            form_id = request.form.get('form_id')
            if form_id == 'form1':
                see_blocks = True
                neighborhood_id = request.form.get('neighborhood_id')
                cursor.execute("""SELECT * FROM Blocks b
                               WHERE b.neighborhood_id = %s""", (neighborhood_id,))
                blocks = cursor.fetchall()
            if form_id == 'form2':
                block_id = request.form.get('block_id')
                cursor.execute("""SELECT * FROM application
                                  WHERE applicant_id = %s AND block_id = %s""", 
                               (session['user_id'], block_id))
                existing_application = cursor.fetchone()

                if existing_application:
                    flash('You have already applied for this block.')
                else:
                    cursor.execute("""SELECT * FROM application
                                      WHERE applicant_id = %s""", 
                                   (session['user_id'],))
                    user_application = cursor.fetchone()

                    if user_application:
                        cursor.execute("""UPDATE application
                                          SET block_id = %s
                                          WHERE applicant_id = %s""", 
                                       (block_id, session['user_id']))
                        flash('Your application has been updated to the new block.')
                    else:
                        cursor.execute("""INSERT INTO application (block_id, applicant_id)
                                          VALUES (%s, %s)""", 
                                       (block_id, session['user_id']))
                        flash('Application sent.')

                    conn.commit()
        cursor.execute("""SELECT 
                            a.application_id, 
                            u.username, 
                            b.name AS block_name, 
                            a.status, 
                            a.created_date, 
                            a.updated_date
                        FROM (
                            SELECT *, ROW_NUMBER() OVER (PARTITION BY a.applicant_id ORDER BY a.created_date DESC) AS rn
                            FROM application a
                        ) a
                        JOIN Users u ON a.applicant_id = u.user_id
                        JOIN blocks b ON a.block_id = b.block_id
                        WHERE a.rn = 1 AND a.applicant_id = %s;
                        """, (session['user_id'],))
        your_app = cursor.fetchall()
        return render_template('applications.html', neighborhoods=neighborhoods, blocks=blocks, see_blocks=see_blocks, your_app=your_app)
    return redirect(url_for('login'))


# /NEW_THREAD
@app.route('/newThread', methods=['GET', 'POST'])
def newThread():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Flag to indicate if a thread was created 
    thread_created = False
    # Check if user is logged in
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        form_id = request.form.get('form_id')
        # FORM 1 Thread form
        if form_id == 'form1':
            if 'recipientType' in request.form and 'email' in request.form:
                email = request.form['email']
                recipientType = request.form['recipientType']


                if recipientType == 'Friend':
                # Check if the email exists in the User's FREINDSHIP table
                    cursor.execute("""
                                    SELECT CASE 
                                        WHEN f.user_id1 = u.user_id THEN f.user_id2 
                                        ELSE f.user_id1 
                                    END AS friend_id,
                                    u2.username,
                                    f.status,
                                    f.user_id1,
                                    f.created_date,
                                    f.update_date
                                    FROM Friendships f
                                    JOIN Users u ON u.user_id = CASE 
                                                        WHEN f.user_id1 = (SELECT user_id FROM Users WHERE email = %s) THEN f.user_id2 
                                                        ELSE f.user_id1 
                                                    END
                                    JOIN Users u2 ON u2.user_id = CASE 
                                                        WHEN f.user_id1 = (SELECT user_id FROM Users WHERE email = %s) THEN f.user_id2 
                                                        ELSE f.user_id1 
                                                    END
                                    WHERE ((SELECT user_id FROM Users WHERE email = %s) = f.user_id1 OR (SELECT user_id FROM Users WHERE email = %s) = f.user_id2)
                                    AND f.status = 'accepted'
                                    """, [email, email, email, email])
                    user = cursor.fetchall()

                    if user:
                        recipient_id = user[0]['friend_id']
                        session['recipient_id']=recipient_id
                        try:
                            cursor.execute("""
                            INSERT INTO Threads (recipient_type, recipient_id) 
                            VALUES (%s, %s) 
                            RETURNING thread_id
                            """, (recipientType, session['recipient_id']))
                            conn.commit()

                            result = cursor.fetchone()
                            if result is not None:
                                thread_id = result[0]
                                print('new thread created, id:', thread_id)
                                flash('New thread created', 'success')
                                # Set the flag to true
                                thread_created = True 
                                session['thread_id'] = thread_id
                            else:
                                flash('Error: Failed to create a new thread.', 'error')
                        except Exception as e:
                            flash(f'Error: {str(e)}', 'error')
                    else:
                        flash('Error: Recipient not found in your relations.', 'error')
                else:
                    flash('Error: Invalid form submission.', 'error')
        # FORM 2 Message form
        if form_id == 'form2':
            if 'message' in request.form and 'title'in request.form:
                # Create variables for easy access
                message = request.form['message']
                title = request.form['title']
                cursor.execute("""INSERT INTO Messages (thread_id, send_to, title, body, author_id) VALUES 
                (%s, %s, %s, %s, %s) RETURNING message_id""", (session['thread_id'], session['recipient_id'], title, message, session['user_id']))
                conn.commit()
                message_id = cursor.fetchone()
                
                
                cursor.execute("""INSERT INTO Read_Status_Recorder (message_id)
                VALUES (%s); """, (message_id))
                conn.commit()
                flash('message sent')
            else:
                flash("Please enter the title and message.")

    return render_template('newThread.html', thread_created = thread_created)

# /REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
    
        _hashed_password = generate_password_hash(password)
    #Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        print(account)
    # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
        # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO users (fullname, username, password_hash, email) VALUES (%s,%s,%s,%s)", (fullname, username, _hashed_password, email))
            conn.commit()
            flash('You have successfully registered!')
    elif request.method == 'POST':
    # Form is empty... (no POST data)
        flash('Please fill out the form!')
    # Show registration form with message (if any)
    return render_template('register.html')

# /LOGIN
@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(username)

 
        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()
 
        if account:
            password_rs = account['password_hash']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['user_id'] = account['user_id']
                session['username'] = account['username']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
            # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
        # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')
 
    return render_template('login.html')

#/LOGOUT
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

# /PROFILE
@app.route('/profile')
def profile(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE user_id = %s', [session['user_id']])
        account = cursor.fetchone()

        cursor.execute('SELECT * FROM block_memberships bm JOIN blocks b ON bm.block_id = b.block_id WHERE bm.user_id = %s', [session['user_id']])
        membership = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account, membership=membership)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# /MESSAGES
@app.route('/messages')
def messages(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute("""
        WITH RankedMessages AS (
            SELECT 
                message_id,
                thread_id,
                reply_to,
                send_to,
                title,
                body,
                author_id,
                location,
                timestamp,
                ROW_NUMBER() OVER (PARTITION BY thread_id ORDER BY timestamp) AS rn
            FROM 
                Messages
            WHERE 
                send_to = 15 OR author_id = 15
        )
        SELECT 
            message_id,
            thread_id,
            reply_to,
            send_to,
            title,
            body,
            author_id,
            location,
            timestamp,
            username
        FROM 
            RankedMessages
        JOIN Users ON RankedMessages.author_id = Users.user_id
        WHERE 
            rn = 1;
        """, [session['user_id'], session['user_id']])
        messages = cursor.fetchall()
        # Show the profile page with account info
        print("Messages fetched:", messages)  # Debugging output
        return render_template('messages.html', messages=messages)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

 #/THREAD/THREAD_ID 
@app.route('/thread/<int:thread_id>', methods=['GET', 'POST'])
def thread(thread_id): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    message_reply = False
    text_display = False
    to_read = None

    # Check if user is logged in
    if 'loggedin' in session:
        if request.method == 'POST':
            form_id = request.form.get('form_id')

            # FORM 1 REPLY 
            if form_id == "form1":
                # CHECK IF FRIENDS
                author_id = request.form['author_id']
                session['author_id'] = author_id

                cursor.execute("""
                    SELECT CASE 
                        WHEN f.user_id1 = u.user_id THEN f.user_id2 
                        ELSE f.user_id1 
                    END AS friend_id,
                    u2.username,
                    f.status,
                    f.user_id1,
                    f.created_date,
                    f.update_date
                    FROM Friendships f
                    JOIN Users u ON u.user_id = CASE 
                                        WHEN f.user_id1 = %s THEN f.user_id2 
                                        ELSE f.user_id1 
                                    END
                    JOIN Users u2 ON u2.user_id = CASE 
                                        WHEN f.user_id1 = %s THEN f.user_id2 
                                        ELSE f.user_id1 
                                    END
                    WHERE (%s = f.user_id1 OR %s = f.user_id2)
                    AND f.status = 'accepted'
                    """, [author_id, author_id, session['user_id'], session['user_id']])
                user = cursor.fetchall()

                if len(user) > 0:
                    message_reply = True
                else:
                    flash("Cannot reply because you are not friends")
            # FORM 2 SEND MESSAGE
            elif form_id == "form2":
                if 'message' in request.form and 'title' in request.form:
                    # Create variables for easy access
                    message = request.form['message']
                    title = request.form['title']
                    cursor.execute("""INSERT INTO Messages (thread_id, send_to, title, body, author_id) VALUES 
                    (%s, %s, %s, %s, %s) RETURNING message_id""", (thread_id, session['author_id'], title, message, session['user_id']))
                    conn.commit()
                    message_id = cursor.fetchone()

                    # Link read recorder
                    cursor.execute("""INSERT INTO Read_Status_Recorder (message_id)
                    VALUES (%s); """, (message_id))
                    conn.commit()
                    flash('Message sent')
                else:
                    flash("Please enter the title and message.", 'error')

            # FORM 3 READ TEXT
            elif form_id == "form3":
                text_display = True
                message_id = request.form['message_id']
                cursor.execute("""SELECT * FROM Messages WHERE message_id = %s""", (message_id,))
                to_read = cursor.fetchone()
                cursor.execute(""" UPDATE Read_Status_Recorder
                                   SET status = 'Read', updated_at = CURRENT_TIMESTAMP
                                   WHERE message_id = %s; """, (message_id,))
                conn.commit()
                flash('Reading text')

        # Fetch messages for the thread
        cursor.execute("""SELECT m.*, u.username, r.status, r.reader_id
                        FROM Messages m
                        JOIN Users u ON u.user_id = m.author_id
                        LEFT JOIN Read_Status_Recorder r ON m.message_id = r.message_id
                        WHERE m.thread_id = %s
                        ORDER BY m.timestamp
                        """, (thread_id,))

        messages = cursor.fetchall()

        return render_template('thread.html', thread_id=thread_id, messages=messages, 
                            message_reply=message_reply, text_display=text_display, to_read=to_read)
        # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# /NEIGHBORS
@app.route('/neighbors', methods=['GET', 'POST'])
def neighbors():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        form_id = request.form.get("form_id")
        if form_id == 'form':
            username = str(request.form.get("username"))
            # Check if there is an existing friendship record
            cursor.execute("""SELECT user_id
                            FROM Users
                            WHERE username = %s;
                        """, [username])
            user_row = cursor.fetchone()
            if user_row:
                user_id2 = int(user_row['user_id'])  # Extract user_id from the result
                cursor.execute("""DELETE FROM Neighbors
                                WHERE neighbor_id2 = %s AND neighbor_id1 = %s;
                                """, [user_id2, session['user_id']])
                conn.commit()
            else:
                flash('User not found')


        # Check if user is loggedin
    if 'loggedin' in session:
        # execute all user's neighbors
        cursor.execute("""SELECT u.username
        FROM Neighbors n
        JOIN Users u ON n.neighbor_id2 = u.user_id
        WHERE n.neighbor_id1 = %s;
        """, [session['user_id']])
        conn.commit()
        neighbors = cursor.fetchall()
        print("Messages fetched:", neighbors)  # Debugging output
        return render_template('neighbors.html', neighbors=neighbors)
    else: # User is not loggedin redirect to login page
        return redirect(url_for('login'))

# /FRIENDSHIPS
@app.route('/friendships', methods=['GET', 'POST'])
def friendships(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        form_id = request.form.get("form_id")
        # HANDLE REJECT FRIEND
        if form_id == 'form1':
            username = str(request.form.get("username"))
            # Check if there is an existing friendship record
            cursor.execute("""SELECT user_id
                            FROM Users
                            WHERE username = %s;
                        """, [username])
            user_row = cursor.fetchone()
            if user_row:
                user_id2 = int(user_row['user_id'])  # Extract user_id from the result
                cursor.execute("""
                    UPDATE Friendships
                    SET status = 'rejected', update_date = CURRENT_TIMESTAMP 
                    WHERE (user_id1 = %s AND user_id2 = %s)
                    OR (user_id1 = %s AND user_id2 = %s);
                """, [session['user_id'], user_id2, user_id2, session['user_id']])
                conn.commit()
            else:
                flash('User not found')

    # Check if user is loggedin
    if 'loggedin' in session:

        # DISPLAY ALL FRIENDS
        cursor.execute("""
        SELECT CASE 
        WHEN f.user_id1 = %s THEN f.user_id2 
        ELSE f.user_id1 
        END AS friend_id,
        u.username,
        f.status,
        f.user_id1,
        f.created_date,
        f.update_date
        FROM Friendships f
        JOIN Users u ON u.user_id = CASE 
                               WHEN f.user_id1 = %s THEN f.user_id2 
                               ELSE f.user_id1 
                           END
        WHERE (%s = f.user_id1 OR %s = f.user_id2)
         AND f.status = 'accepted'
        """, [session['user_id'], session['user_id'], session['user_id'], session['user_id']])
        friends = cursor.fetchall()
        # Show the profile page with account info
        print("Messages fetched:", friends)  # Debugging output
        return render_template('friendships.html', friends=friends)
    # User is not loggedin redirect to login page
    else:
        return redirect(url_for('login'))

# /MEET
@app.route('/meet', methods=['GET', 'POST'])
def meet(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        form_id = request.form.get('form_id')
        # NEIGHBOR SECTION
        if form_id == 'form2':
            neighbor_id2 = int(request.form.get('neighbor_id'))
            # Check if there is an existing friendship record
            cursor.execute("""
            SELECT COUNT(*) FROM Neighbors 
            WHERE (neighbor_id1 = %s AND neighbor_id2 = %s)
            OR (neighbor_id1 = %s AND neighbor_id2 = %s);
            """, (session['user_id'], neighbor_id2, neighbor_id2, session['user_id']))
            existing_record_count = cursor.fetchone()[0]

            if existing_record_count > 0:
                # Update existing record
                cursor.execute("""
                    UPDATE Neighbors 
                    SET update_date = CURRENT_TIMESTAMP 
                    WHERE (neighbor_id1 = %s AND neighbor_id2 = %s)
                    OR (neighbor_id1 = %s AND neighbor_id2 = %s);
                """, (session['user_id'], neighbor_id2, neighbor_id2, session['user_id']))
                conn.commit()
                flash('Neighbor record updated!')
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO Neighbors (neighbor_id1, neighbor_id2)
                    VALUES (%s, %s);
                """, (session['user_id'], neighbor_id2))
                conn.commit()
                flash('You have successfully added a neighbor!')

        # FRIEND SECTION
        if form_id == 'form1':
            user_id2 = int(request.form.get('user_id'))
            # Check if there is an existing friendship record
            cursor.execute("""
                SELECT COUNT(*) FROM Friendships 
                WHERE (user_id1 = %s AND user_id2 = %s)
                OR (user_id1 = %s AND user_id2 = %s);
            """, (session['user_id'], user_id2, user_id2, session['user_id']))
            existing_record_count = cursor.fetchone()[0]

            if existing_record_count > 0:
                # Update existing record
                cursor.execute("""
                    UPDATE Friendships 
                    SET status = 'pending', update_date = CURRENT_TIMESTAMP 
                    WHERE (user_id1 = %s AND user_id2 = %s)
                    OR (user_id1 = %s AND user_id2 = %s);
                """, (session['user_id'], user_id2, user_id2, session['user_id']))
                conn.commit()
                flash('Friendship request updated!')
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO Friendships (user_id1, user_id2, status)
                    VALUES (%s, %s, 'pending');
                """, (session['user_id'], user_id2))
                conn.commit()
                flash('You have successfully requested!')

    # Check if user is loggedin
    if 'loggedin' in session:
        # ALL NOT FRIENDS 
        cursor.execute("""
            SELECT *
            FROM Users
            WHERE user_id != %s
            AND user_id NOT IN (
                SELECT CASE
                    WHEN user_id1 = %s THEN user_id2
                    ELSE user_id1
                END AS friend_id
                FROM Friendships
                WHERE user_id1 = %s OR user_id2 = %s
            )

            UNION

            SELECT u.*
            FROM Users u
            JOIN Friendships f ON u.user_id = CASE
                WHEN f.user_id1 = %s THEN f.user_id2
                ELSE f.user_id1
            END
            WHERE (f.user_id1 = %s OR f.user_id2 = %s)
            AND f.status = 'rejected'""", [session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id']])
        users = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM Users
            WHERE user_id != %s
            AND user_id NOT IN (
                SELECT neighbor_id2
                FROM Neighbors
                WHERE neighbor_id1 = %s
            )
        """, [session['user_id'], session['user_id']])

        neighbors=cursor.fetchall()

        # Show the profile page with account info
        print("Messages fetched:", users)  # Debugging output
        print("Messages fetched:", neighbors)  # Debugging output
        return render_template('meet.html', users=users, neighbors=neighbors)
    else:
        # User is not loggedin redirect to login page
        return redirect(url_for('login'))

# /REQUESTS
@app.route('/requests', methods=['GET', 'POST'])
def requests(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        user_id2 = int(request.form.get('user_id1'))
        action = str(request.form.get('action'))

        if action == "Accept":
            cursor.execute("""
                            UPDATE Friendships
                            SET status = 'accepted', 
                                update_date = CURRENT_TIMESTAMP
                            WHERE user_id1 = %s 
                            AND user_id2 = %s
                """, [user_id2, session['user_id']])
            conn.commit()
            flash('You are now friends!')
        elif action == "Reject":
            cursor.execute("""
                            UPDATE Friendships
                            SET status = 'rejected', 
                                update_date = CURRENT_TIMESTAMP
                            WHERE user_id1 = %s 
                            AND user_id2 = %s
                """, [user_id2, session['user_id']])
            conn.commit()
            flash('You are not friends!')

    # Check if user is loggedin
    if 'loggedin' in session:
        # SELECT ALL FRIENDS WHO REQUESTED YOU
        cursor.execute("""
                SELECT * 
                FROM Friendships f
                JOIN Users u ON u.user_id = f.user_id1
                WHERE f.user_id2 = %s 
                AND status = 'pending';
            """, [session['user_id']])
        users = cursor.fetchall()

        # Show the profile page with account info
        print("Messages fetched:", users)  # Debugging output
        return render_template('requests.html', users=users)
        # User is not loggedin redirect to login page
    else:
        return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)



    