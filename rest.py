from __future__ import print_function # In python 2.7
from flask import Flask, redirect, url_for, session, request, jsonify ,render_template
from flask_oauthlib.client import OAuth
#from flask_mysqldb import MySQL
from flaskext.mysql import MySQL
#from flask.ext.mysql import MySQL
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



@app.route('/')
def first():
    return 'REST'

@app.route('/rest' , methods=['GET' , 'POST'])
def rest():
    searchq = request.args.get('search')
    return searchq




if __name__ == '__main__':
    app.run()
