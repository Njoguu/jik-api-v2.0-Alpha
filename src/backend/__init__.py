from flask import Flask, render_template, request, jsonify
import os
import sys
path = os.getcwd()
sys.path.append(path+"/src/")
from backend import database as dbcons
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError
import logging
import hashlib
import json
from flasgger import Swagger, swag_from
from backend.config.swagger import swagger_config,template

def create_app(test_config=None):

    template_dir = os.getcwd() + '/src/frontend/templates'
    static_dir = os.getcwd() + '/src/frontend/static'

    mailchimp = Client()
    mailchimp.set_config({
        'api_key': os.environ.get('MAILCHIMP_API_KEY'),
        'server': os.environ.get('MAILCHIMP_REGION'),
    })

    logger = logging.getLogger(__name__)
    
    app = Flask(__name__, instance_relative_config=True, template_folder=template_dir, static_folder=static_dir)    
    keyword = ""
    specified_date = "" 


    if test_config is None:

        app.config.from_mapping(
            SECRET_KEY=os.environ.get("SECRET_KEY"),
            SQLALCHEMY_DATABASE_URI=os.environ.get("SQLALCHEMY_DB_URI"),
            SQLALCHEMY_TRACK_MODIFICATIONS=False
        )
        SWAGGER = {
                "title" : "jikAPI",
                "uiversion" : 3,
        }

    else:
        app.config.from_mapping(test_config)

    Swagger(app, config=swagger_config, template=template)

    @app.route('/')
    def homepage():
        message = "Streamline your job search with this Job Search API. Check it out! #jobs #API"
        url = "https://jikapi.herokuapp.com"

        tweet_link = "https://twitter.com/intent/tweet?text=" + message + "&url=" + url
        linkedin_link = "https://www.linkedin.com/sharing/share-offsite/?url=" + url
        facebook_link = "https://www.facebook.com/sharer/sharer.php?u=" + url
        
        return render_template('index.html', tweet_link=tweet_link, linkedin_link=linkedin_link, facebook_link=facebook_link)


    @app.route('/api/v2/jobs', methods=['GET'])
    @swag_from('./docs/postings/jobs.yaml')
    def available_jobs():
        data = dbcons.getData(tableName=os.environ.get('TABLENAME'))
        jobs = data[0][0]
        return jsonify(jobs)
        
    # Using Query parameters
    # /api/v2/jobs/keyword?jobname=Software+Developer
    @app.route('/api/v2/jobs/keyword')
    def qspecific_jobs():
        
        global keyword
        keyword = request.args.get('jobname', '', type=str)

        data = dbcons.get_specific_job(tableName=os.environ.get('TABLENAME'))
        jobs = data[0][0]
        return jsonify(jobs)
        
    
    @app.route('/api/v2/jobs/keyword', methods = ['POST'])
    @swag_from('./docs/postings/use_keyword.yaml')
    def specific_jobs():
        reqJSON = request.get_json()

        global keyword
        keyword = reqJSON['keyword']

        data = dbcons.get_specific_job(tableName=os.environ.get('TABLENAME'))
        jobs = data[0][0]
        return jsonify(jobs)

    @app.route('/api/v2/jobs', methods=['POST'])
    @swag_from('./docs/postings/use_date.yaml')
    def date_specified():
        reqJSON = request.get_json()

        global specified_date
        specified_date = reqJSON['specified_date']

        data = dbcons.get_job_of_specific_date(tableName=os.environ.get('TABLENAME'))
        jobs = data[0][0]
        return jsonify(jobs)

    @app.route('/api/v2/newsletter/subscribe', methods=['POST'])
    def subscribe():
        # add the email address to your mailing list here
        if request.method == 'POST':
            try:
                email = request.form['email']
                form_email_hash = hashlib.md5(email.encode('utf-8').lower()).hexdigest()
                member_update = {
                    'status': 'subscribed',
                }
                response = mailchimp.lists.set_list_member(
                    os.environ.get('MAILCHIMP_MARKETING_AUDIENCE_ID'),
                    form_email_hash,
                    member_update,
                )
                logger.info(f'API call successful: {response}')
                data = '{"title": "Successfully subscribed!","message": "You have been successfully subscribed to our mailing list."}'
                json_data = json.loads(data)
                return render_template('message.html', json_data=json_data)

            except ApiClientError as error:
                logger.error(f'An exception occurred: {error.text}')
                data = data = '{"title": "Failed to subscribe!","message": "Oops, something went wrong."}'
                json_data = json.loads(data)
                return render_template('message.html', json_data=json_data)

    @app.route('/api/v2/newsletter/unsubscribe', methods=['GET','POST'])
    def unsubscribe():
        if request.method == 'POST':
            try:
                email = request.form['email']
                form_email_hash = hashlib.md5(email.encode('utf-8').lower()).hexdigest()
                member_update = {
                    'status': 'unsubscribed',
                }
                response = mailchimp.lists.update_list_member(
                    os.environ.get('MAILCHIMP_MARKETING_AUDIENCE_ID'),
                    form_email_hash,
                    member_update,
                )
                logger.info(f'API call successful: {response}')
                data = '{"title": "Successfully unsubscribed!","message": "You have been successfully unsubscribed from our mailing list."}'
                json_data = json.loads(data)
                return render_template('message.html', json_data=json_data)

            except ApiClientError as error:
                logger.error(f'An exception occurred: {error.text}')
                data = data = '{"title": "Failed to unsubscribe!","message": "Oops, something went wrong. Could not subscribe you to our mailing list."}'
                json_data = json.loads(data)
                return render_template('message.html', json_data=json_data)

        return render_template('unsubscribe.html')

    # TODO --> SEND PING TO TESTS
    @app.route('/api/mailchimp/ping')
    def mailchimp_ping_view():
        response = mailchimp.ping.get()
        return jsonify(response)


    return app
    