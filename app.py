from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_mysqldb import MySQL
import config
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.secret_key = "b';\x90q\xe6x\x9c!iZxH\xa1\x81P\xe6f'"

app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

from flask_mail import Mail, Message
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'divyamadineni@iitgn.ac.in'
app.config['MAIL_PASSWORD'] = 'njkwpjvnodqrbbkn'
app.config['MAIL_USE_SSL'] = True

from flask_mail import Mail, Message
mail = Mail(app)
@app.route('/send_email', methods=['POST'])
def send_ema():
    template_selected = request.form.get('template') 
    recipients = request.form.get('recipients')  
    recipient_emails = recipients.split(",") if recipients else []  
    subject = request.form['subject']
    content = request.form['content']
    sender = 'divyamadineni@iitgn.ac.in'  # Specify sender
    if template_selected == 'template1':
        try:
            all_recipient_emails = []  # Store all individual recipient addresses
            for recipient_email in recipient_emails:
                is_group_email, group_id = is_group(recipient_email)  # Check if the recipient is a group and get the group_id
                if is_group_email:
                    group_members = retrieve_group_members(recipient_email)  # Retrieve group members from database using group_id
                    all_recipient_emails.extend(group_members) 
                else:
                    all_recipient_emails.append(recipient_email)
            
            if not all_recipient_emails:
                return 'No recipients have been added.', 400  # Return an error if no recipients are added
            
            msg = Message(subject, recipients=all_recipient_emails, sender=sender)
            msg.body = content
            mail.send(msg)
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO Email (Email_subject, Email_content, DeliveryStatus, Timestamp, SMTP_serveraddress, User_id, Template_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (subject, content, 'Delivered', datetime.now(), 'smtp.gmail.com', 1, 1))  # Replace 'your_smtp_server_address' with the actual SMTP server address, and 1 with the actual user and template IDs
            emaillog_id = cur.lastrowid
            for recipient_email in recipient_emails:
                is_group_email, group_id = is_group(recipient_email)  # Check if the recipient is a group and get the group_id
                if is_group_email:
                    cur.execute("INSERT INTO Group_receiver(EmailLog_id,Group_id) VALUES (%s,%s)",(emaillog_id, group_id))
                else:
                    recipient_id = fetch_recipient_id(recipient_email)
                    cur.execute("INSERT INTO Individual_receiver(EmailLog_id,Recipient_id) VALUES (%s,%s)",(emaillog_id, recipient_id))
            mysql.connection.commit()
            cur.close()
            return 'Email sent successfully!'
        except Exception as e:
            return f'Failed to send email. Error: {str(e)}', 500
    else:
        try:
            cur = mysql.connection.cursor()
            all_recipient_emails = []  # Store all individual recipient addresses
            for recipient_email in recipient_emails:
                is_group_email, group_id = is_group(recipient_email)  # Check if the recipient is a group and get the group_id
                if is_group_email:
                    group_members = retrieve_group_members(recipient_email)  # Retrieve group members from database using group_id
                    all_recipient_emails.extend(group_members)
                else:
                    all_recipient_emails.append(recipient_email)

            for recipient_email in all_recipient_emails:
                recipient_name = get_recipient_name(recipient_email)  # Retrieve recipient's name from database
                modified_content = content.replace('{{name}}', recipient_name)  # Replace '{{name}}' with the recipient's name in the email content
                msg = Message(subject, recipients=[recipient_email], sender=sender)
                msg.body = modified_content
                mail.send(msg)

            # Perform database operations to log email sending status and recipients
            cur.execute("INSERT INTO Email (Email_subject, Email_content, DeliveryStatus, Timestamp, SMTP_serveraddress, User_id, Template_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (subject, content, 'Delivered', datetime.now(), 'smtp.gmail.com', 1, 1))  # Replace 'your_smtp_server_address' with the actual SMTP server address, and 1 with the actual user and template IDs
            emaillog_id = cur.lastrowid
            for recipient_email in recipient_emails:
                is_group_email, group_id = is_group(recipient_email)  # Check if the recipient is a group and get the group_id
                if is_group_email:
                    cur.execute("INSERT INTO Group_receiver(EmailLog_id,Group_id) VALUES (%s,%s)",(emaillog_id, group_id))
                else:
                    recipient_id = fetch_recipient_id(recipient_email)
                    cur.execute("INSERT INTO Individual_receiver(EmailLog_id,Recipient_id) VALUES (%s,%s)",(emaillog_id, recipient_id))
            mysql.connection.commit()
            cur.close()
            return 'Email sent successfully!'
        except Exception as e:
            return f'Failed to send email. Error: {str(e)}'

def fetch_recipient_id(recipient_email):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT Recipient_id FROM RecipientList WHERE RecipientEmail_id = %s", (recipient_email,))
        recipient_id = cur.fetchone()  # Fetch the recipient_id
        cur.close()
        return recipient_id[0] if recipient_id else None
    except Exception as e:
        return None  # Return None if there's an error or recipient not found

def is_group(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT Group_id FROM Email_Group WHERE Group_address = %s", (email,))
    group = cur.fetchone()
    cur.close()
    return group is not None, group[0] if group else None

def retrieve_group_members(group_address):
    cur = mysql.connection.cursor()
    cur.execute("SELECT rl.RecipientEmail_id FROM Email_Group eg JOIN Memberof m ON eg.Group_id = m.Group_id JOIN RecipientList rl ON m.Recipient_id = rl.Recipient_id WHERE eg.Group_address = %s", (group_address,))
    group_members = cur.fetchall()
    email_addresses = [member[0] for member in group_members]
    cur.close()
    return email_addresses


def get_recipient_name(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT Recipient_name FROM RecipientList WHERE RecipientEmail_id = %s", (email,))
    recipient = cur.fetchone()
    cur.close()
    return recipient[0] if recipient else ''


# @app.route('/send_email', methods=['POST'])
# def send_email():
#     template_selected = request.form.get('template')
#     recipients = request.form.get('recipients')  # Get selected group and recipient addresses
#     recipient_emails = recipients.split(",") if recipients else []  # Split the string of recipients by comma or initialize an empty list
#     subject = request.form['subject']
#     content = request.form['content']
#     sender = 'divyamadineni@iitgn.ac.in'  # Specify sender
#     try:
#         all_recipient_emails = []  # Store all individual recipient addresses
#         for recipient_email in recipient_emails:
#             is_group_email, group_id = is_group(recipient_email)  # Check if the recipient is a group and get the group_id
#             if is_group_email:
#                 group_members = retrieve_group_members(group_id)  # Retrieve group members from database using group_id
#                 for member_email in group_members:
#                     msg = Message(subject, recipients=[member_email], sender=sender)
#                     msg.body = content if template_selected == 'template1' else content.replace('{{name}}', get_recipient_name(member_email))  # Replace {{name}} with recipient name if template is 1
#                     mail.send(msg)
#                     all_recipient_emails.append(member_email)  # Add recipient's email to the list
#             else:
#                 msg = Message(subject, recipients=[recipient_email], sender=sender)
#                 msg.body = content if template_selected == 'template1' else content.replace('{{name}}', get_recipient_name(recipient_email))  # Replace {{name}} with recipient name if template is 1
#                 mail.send(msg)
#                 all_recipient_emails.append(recipient_email)  # Add recipient's email to the list

#         if not all_recipient_emails:
#             return 'No recipients have been added.', 400  # Return an error if no recipients are added

#         # Insert email details into the database
#         cur = mysql.connection.cursor()
#         cur.execute("INSERT INTO Email (Email_subject, Email_content, DeliveryStatus, Timestamp, SMTP_serveraddress, User_id, Template_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
#                     (subject, content, 'Delivered', datetime.now(), 'smtp.gmail.com', 1, 1))  # Replace 'your_smtp_server_address' with the actual SMTP server address, and 1 with the actual user and template IDs
#         emaillog_id = cur.lastrowid

#         for recipient_email in all_recipient_emails:
#             is_group_email, group_id = is_group(recipient_email)  # Check if the recipient is a group and get the group_id
#             if is_group_email:
#                 cur.execute("INSERT INTO Group_receiver(EmailLog_id,Group_id) VALUES (%s,%s)", (emaillog_id, group_id))
#             else:
#                 recipient_id = fetch_recipient_id(recipient_email)
           
#                 cur.execute("INSERT INTO Individual_receiver(EmailLog_id,Recipient_id) VALUES (%s,%s)", (emaillog_id, recipient_id))
#         mysql.connection.commit()
#         cur.close()
#         return 'Email sent successfully!'
#     except Exception as e:
#         return f'Failed to send email. Error: {str(e)}', 500

# def is_group(email_address):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT Group_id FROM Email_Group WHERE group_address = %s", (email_address,))
#     result = cur.fetchone()
#     cur.close()
#     return result is not None, result[0] if result else None

# def retrieve_group_members(group_address):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT rl.RecipientEmail_id FROM Email_Group eg JOIN Memberof m ON eg.Group_id = m.Group_id JOIN RecipientList rl ON m.Recipient_id = rl.Recipient_id WHERE eg.Group_address = %s", (group_address,))
#     group_members = cur.fetchall()
#     email_addresses = [member[0] for member in group_members]
#     cur.close()
#     return email_addresses

# def get_recipient_name(email):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT Recipient_name FROM RecipientList WHERE RecipientEmail_id = %s", (email,))
#     recipient = cur.fetchone()
#     cur.close()
#     return recipient[0] if recipient else ''


# def fetch_recipient_id(recipient_email):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT Recipient_id FROM RecipientList WHERE RecipientEmail_id = %s", (recipient_email,))
#     result = cur.fetchone()
#     cur.close()
#     return result[0] if result else None




@app.route('/sentEmails')
def sent_emails():
    cur = mysql.connection.cursor()
    usermailid = session.get('usermailid') 
    cur.execute("""
        SELECT e.EmailLog_id, e.Email_subject, e.Email_content, e.DeliveryStatus, e.Timestamp, 
               GROUP_CONCAT(DISTINCT CONCAT(g.group_address, ' (Group)') SEPARATOR ';') AS group_addresses,
               GROUP_CONCAT(DISTINCT CONCAT(r.RecipientEmail_id, ' (Individual)') SEPARATOR ';') AS individual_addresses
        FROM Email e
        LEFT JOIN Group_receiver gr ON e.EmailLog_id = gr.EmailLog_id
        LEFT JOIN Email_Group g ON gr.Group_id = g.Group_id
        LEFT JOIN Individual_receiver ir ON e.EmailLog_id = ir.EmailLog_id
        LEFT JOIN RecipientList r ON ir.Recipient_id = r.Recipient_id
        GROUP BY e.EmailLog_id, e.Email_subject, e.Email_content, e.DeliveryStatus, e.Timestamp
    """)
    emails = cur.fetchall()
    cur.close()
    return render_template('sentEmails.html', emails=emails,usermailid=usermailid)


from flask import request, jsonify

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    usermailid=None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM User WHERE UserEmail_id=%s", [email])
        User = cur.fetchone()
        if User and check_password_hash(User[3], password):  # Assuming User table columns are id, email, password
            session['user_id'] = User[0]
            usermailid=User[2]
            session['usermailid'] = usermailid
            session.pop('selected_groups', None)
            session.pop('selected_recipients', None)
            return redirect(url_for('home',usermailid=usermailid))
        else:
            error = 'Invalid Credentials. Please try again.'
            return error
    return render_template('login.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)
        app.logger.info('Received POST request to add User: User_name - %s, UserEmail_id - %s, Passwordhash - %s', username, email, hashed_password)
        
        cur = mysql.connection.cursor()

        try:
            cur.execute("INSERT INTO User(User_name, UserEmail_id, Passwordhash) VALUES (%s, %s, %s)", (username, email, hashed_password))
            mysql.connection.commit()
            app.logger.info('User added successfully: User_name - %s, UserEmail_id - %s, Passwordhash - %s', username, email, hashed_password)
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            error = 'Registration failed. User already exists.'  # Set an error message
            app.logger.error('Error adding User to database: %s', str(e))
            return error
        finally:
            cur.close()

    return render_template('registration.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Retrieve usermailid from session
    usermailid = session.get('usermailid')  

    # Initialize selected_groups and selected_recipients variables from session
    selected_groups = session.get('selected_groups', [])
    selected_recipients = session.get('selected_recipients', [])

    if request.method == 'POST':
        # Check if the form contains selected group IDs
        if 'groups[]' in request.form:
            # Get the selected groups from the form
            new_selected_groups = request.form.getlist('groups[]')
            # Append the newly selected groups to the existing list
            selected_groups += new_selected_groups

        # Check if the form contains selected recipient IDs
        if 'recipients[]' in request.form:
            # Get the selected recipients from the form
            new_selected_recipients = request.form.getlist('recipients[]')
            # Append the newly selected recipients to the existing list
            selected_recipients += new_selected_recipients

        # Remove duplicates from the lists
        selected_groups = list(set(selected_groups))
        selected_recipients = list(set(selected_recipients))

        # Update session variables with the updated lists
        session['selected_groups'] = selected_groups
        session['selected_recipients'] = selected_recipients
    else:
        # If it's a GET request, clear the session data for selected groups and recipients
        session.pop('selected_groups', None)
        session.pop('selected_recipients', None)
    # Render the home template and pass selected groups and recipients as variables
    return render_template('home.html', selected_groups=selected_groups, usermailid=usermailid, selected_recipients=selected_recipients)

@app.route('/seeRecipientList')
def RL():
    cur = mysql.connection.cursor()
    cur.execute("SELECT Recipient_id, RecipientEmail_id, Recipient_name, Gender, Company, Age FROM RecipientList")
    recipients = cur.fetchall()
    cur.close()
    return render_template('seeRecipientList.html', recipients=recipients)

@app.route('/seeGroups')
# def seeGroups():
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT Group_id, Group_name, Description, Criteria FROM Email_Group")
#     groups = cur.fetchall()
#     cur.close()
#     return render_template('seeGroups.html', groups=groups)
def groups():
    cur = mysql.connection.cursor()
    cur.execute("SELECT Group_id, Group_name FROM Email_Group")
    groups = cur.fetchall()

    # Fetching group details might be more complex depending on your schema
    group_details = {}
    for group in groups:
        group_id = group[0]
        # Specify the table for ambiguous columns (e.g., RecipientList.Recipient_id)
        cur.execute("""
            SELECT RecipientList.Recipient_id, RecipientList.RecipientEmail_id, RecipientList.Recipient_name, RecipientList.Gender, RecipientList.Age 
            FROM RecipientList 
            JOIN Memberof ON RecipientList.Recipient_id = Memberof.Recipient_id 
            WHERE Memberof.Group_id = %s
        """, (group_id,))
        group_details[group_id] = cur.fetchall()
    return render_template('seeGroups.html', groups=groups, group_details=group_details)

@app.route('/delete-groups', methods=['POST'])
def delete_groups():
    data = request.get_json()
    group_ids = data['group_ids']
    group_ids = [int(id) for id in group_ids]

    placeholders = ','.join(['%s'] * len(group_ids))

    memberof_query = "DELETE FROM Memberof WHERE Group_id IN ({})".format(placeholders)

    email_group_query = "DELETE FROM Email_Group WHERE Group_id IN ({})".format(placeholders)

    cur = mysql.connection.cursor()
    cur.execute(memberof_query, group_ids)
    cur.execute(email_group_query, group_ids)
    
    mysql.connection.commit()  
    cur.close()

    return jsonify({'success': True})

# @app.route('/rename-group', methods=['POST'])
# def rename_group():
#     data = request.get_json()
#     group_id = data['group_id']
#     new_name = data['new_name']
#     # Add your logic to rename the group in the database


#     return jsonify({'success': True})

@app.route('/rename-group', methods=['POST'])
def rename_group():
    data = request.get_json()
    group_id = data['group_id']
    new_name = data['new_name']
    
    # Add your logic to rename the group in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Email_Group SET Group_name = %s WHERE Group_id = %s", (new_name, group_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True})

@app.route('/rename-recipient', methods=['POST'])
def rename_recipient_seeGroups():
    data = request.get_json()
    recipient_id = data['recipient_id']
    new_name = data['new_name']
    
    # Add your logic to rename the group in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE RecipientList SET Recipient_name = %s WHERE Recipient_id = %s", (new_name, recipient_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True})

@app.route('/delete-recipients', methods=['POST'])
def delete_recipients():
    data = request.get_json()
    recipient_ids = data['recipient_ids']
    recipient_ids = [int(id) for id in recipient_ids]

    placeholders = ','.join(['%s'] * len(recipient_ids))

    memberof_query = "DELETE FROM Memberof WHERE Recipient_id IN ({})".format(placeholders)

    email_recipient_query = "DELETE FROM RecipientList WHERE Recipient_id IN ({})".format(placeholders)

    cur = mysql.connection.cursor()
    cur.execute(memberof_query, recipient_ids)
    cur.execute(email_recipient_query, recipient_ids)
    
    mysql.connection.commit()  
    cur.close()

    return jsonify({'success': True})

@app.route('/chooseExistedGroups',methods=['GET', 'POST'])
def CEG():
    if request.method == 'POST':
        selected_groups = request.form.getlist('selected_groups')
        return render_template('home.html', selected_groups=selected_groups)
    cur = mysql.connection.cursor()
    cur.execute("SELECT Group_id, Group_name, group_address FROM Email_Group")
    groups = cur.fetchall()
    cur.close()
    return render_template('chooseExistedGroups.html', groups=groups)

@app.route('/chooseRecipientList', methods=['GET', 'POST'])
def CRL():
    # if request.method == 'POST':
    #     selected_recipients = request.form.getlist('selected_groups')
    #     return render_template('home.html', selected_groups=selected_groups)
    cur = mysql.connection.cursor()
    cur.execute("SELECT Recipient_id, Recipient_name, RecipientEmail_id FROM RecipientList")
    recipients = cur.fetchall()
    cur.close()
    return render_template('chooseRecipientList.html', recipients=recipients)


@app.route('/insertRecipient')
def insert_recipient_page():
    return render_template('insertRecipient.html')

@app.route('/insertRecipient', methods=['POST'])
def insert_recipient():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    recipient_email = request.form['recipient_email']
    recipient_name = request.form['recipient_name']
    gender = request.form['gender']
    company = request.form['company']
    age = request.form['age']

    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO RecipientList (RecipientEmail_id, User_id, Recipient_name, Gender, Company, Age) VALUES (%s, %s, %s, %s, %s, %s)",
                    (recipient_email, session['user_id'], recipient_name, gender, company, age))
        mysql.connection.commit()
        return redirect(url_for('home'))
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
@app.route('/deleteRecipients', methods=['POST'])
def delete_r():
    try:
        # Get the list of recipient IDs to delete from the request data
        recipient_ids = request.json.get('recipientIds')

        if recipient_ids:
            # Connect to the database
            cur = mysql.connection.cursor()

            # Delete recipients from the Memberof table
            query_memberof = "DELETE FROM Memberof WHERE Recipient_id IN (%s)"
            query_params_memberof = ','.join(['%s'] * len(recipient_ids))
            query_memberof = query_memberof % query_params_memberof
            cur.execute(query_memberof, tuple(recipient_ids))

            # Delete recipients from the RecipientList table
            query_recipientlist = "DELETE FROM RecipientList WHERE Recipient_id IN (%s)"
            query_params_recipientlist = ','.join(['%s'] * len(recipient_ids))
            query_recipientlist = query_recipientlist % query_params_recipientlist
            cur.execute(query_recipientlist, tuple(recipient_ids))

            # Commit changes to the database
            mysql.connection.commit()

            # Close cursor and database connection
            cur.close()

            # Return success message
            return jsonify({'message': 'Recipients deleted successfully'}), 200
        else:
            # If no recipient IDs are provided in the request data
            return jsonify({'error': 'No recipient IDs provided in the request'}), 400

    except Exception as e:
        # If an error occurs during deletion
        return jsonify({'error': 'Error deleting recipients: {}'.format(str(e))}), 500

# @app.route('/insertRecipient_RL')
# def insert_recipient_page_RL():
#     return render_template('insertRecipient_RL.html')

@app.route('/insertRecipient_RL')
def insert_recipient_page_RL():
    group_id = request.args.get('group_id')
    return render_template('insertRecipient_RL.html', group_id=group_id)


@app.route('/insertRecipient_RL', methods=['POST'])
def insert_recipient_RL():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    recipient_email = request.form['recipient_email']
    recipient_name = request.form['recipient_name']
    gender = request.form['gender']
    company = request.form['company']
    age = request.form['age']
    group_id = request.form['group_id']  # Retrieve group_id from the form data

    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO RecipientList (RecipientEmail_id, User_id, Recipient_name, Gender, Company, Age) VALUES (%s, %s, %s, %s, %s, %s)",
                    (recipient_email, session['user_id'], recipient_name, gender, company, age))
        recipient_id = cur.lastrowid
        cur.execute("INSERT INTO Memberof (Group_id, Recipient_id) VALUES (%s, %s)",
                    (group_id,recipient_id))
        mysql.connection.commit()
        return redirect(url_for('home'))
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

@app.route('/insertGroup')
def insert_group_page():
    return render_template('insertGroup.html')

@app.route('/insertGroup', methods=['POST'])
def insert_group():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    Group_name = request.form['Group_name']
    group_address =request.form['group_address']
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Email_Group (Group_name,group_address) VALUES (%s,%s)",
                    (Group_name,group_address))
        mysql.connection.commit()
        return redirect(url_for('home'))
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

if __name__ == '__main__':
    app.run(debug=True)
