# HomeDoctor

An application that provides a medical diagnosis and recommendation on Google Assistant
  * Provides a medical diagnosis based on your symptoms
  * Asks follow-up questions to provide a more accurate diagnosis
  * Gives context about the conditions(s) you may have and a recommendation on what to do about it

## USAGE
  * "Ok Google, talk to HomeDoctor" to speak with the application
  * "I'm a 30 year old male" to identify your age and sex
  * "I have a runny nose and a sore throat" to identify your symptoms
  * "Yes (or no)" to answer follow up questions
  
# BUILD/INSTALLATION INSTRUCTIONS:
1. Load the HomeDoctor.zip agent into API.AI
2. Move the web backend files (main.py, requirements.txt) into your server of choice
3. Install requirements with `pip install -r requirements.txt`
4. Obtain API credentials from Infermedica and Firebase. Edit `secrets.example.py` and save as `secrets.py`
4. Run backend with `python main.py`
5. Point the API.AI webhook endpoint to https://(your-server-ip)/webhook
6. Setup the API.AI google assistant integration (use same account linked to your Google Home)
7. Talk to your Google Home! (see usage)

## OTHER SOURCES OF DOCUMENTATION

* https://developers.google.com/actions/
* https://docs.api.ai/
* https://developer.infermedica.com/docs/introduction

## Contributor Guide
[CONTRIBUTING.md](CONTRIBUTING.md)

## Contributions
[CONTRIBUTORS.md](CONTRIBUTORS.md)

## License 
[LICENSE.md](LICENSE.md)
