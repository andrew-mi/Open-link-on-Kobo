import requests
import json
from flask import Flask, request, redirect, Response
from time import sleep
import bleach

app = Flask(__name__, static_url_path='', static_folder='static')

ks_apiurl = 'https://api.keyvalue.xyz'
ks_schemename = '905e3f85-kobo'
ks_validTokenLength = 8

token_cache = None

def GetNewToken():
    r = requests.post(f"{ks_apiurl}/new/{ks_schemename}")
    new_token = r.text.replace(f"/{ks_schemename}","").replace(f"{ks_apiurl}/","").rstrip()
    requests.post(f"{ks_apiurl}/{new_token}/{ks_schemename}", data = json.dumps({"scheme_version":"1"}))
    global token_cache
    token_cache = new_token
    return new_token

@app.route('/')
def home():
    if "Kobo" in request.user_agent.string:
        return NewKobo()
    else:
        block_message = '''<blockquote>Bookmark this page on your Kobo and enter the generated access code</blockquote>'''
        if request.args.get('error') == '1':
            block_message = '''<blockquote style="border-color:red;background-color:salmon;">Invalid access code</blockquote>'''
        return '''
        <html>
            <head>
                <title>Send to Kobo</title>
                <link rel="stylesheet" href="/vanilla.css">
                <link rel="stylesheet" href="/style.css">
            </head>
            <body>
                <h1>Send to Kobo</h1>
                <p>This site makes it easier to access epub download links on your Kobo.</p>
                ''' + block_message + '''
                <form action="/connect" method="get">
                    <input type="text" name="token" placeholder="Access Code" maxlength="10" style="font-family: monospace;font-weight: bold;">
                    <input type="submit" class="submitButton" value="Connect to Kobo">
                </form>
            </body>
            <footer>
                <hr>
                <p><small>
                    Created by <a href="https://github.com/andrew-mi">Andrew Mitchell</a>.
                    <br>
                    Not using a Kobo? <a href="/fake-kobo-ua">Treat this device as a recipient anyway</a>
                </small></p>
            </footer>
        </html>
        '''

@app.route('/connect')
def Connect():
    if 'token' not in request.args:
        return redirect('/')
    token = request.args.get('token')
    global token_cache
    if token != token_cache:
        if len(token) != ks_validTokenLength:
            return redirect('/?error=1')
    r = requests.get(f"{ks_apiurl}/{token}/{ks_schemename}")
    if r.status_code!=200:
        return redirect('/?error=1')
    token_cache = token
    data = r.json()
    if 'url' in data:
        content = bleach.linkify(bleach.clean(str(data['url'])))
    else:
        content = '''<p style="text-align:center">No link saved</p><a class="button" href="javascript:window.location.reload(true)">Refresh</a>'''
    return '''
    <html>
        <head>
            <title>Send to Kobo</title>
            <link rel="stylesheet" href="/vanilla.css">
            <link rel="stylesheet" href="/style.css">
        </head>
        <body>
            <h1>Send to Kobo</h1>
            <p>This site makes it easier to access epub download links on your Kobo.</p>
            <blockquote style="border-color:green;background-color:palegreen;">Connected to <strong class="token">''' + token + '''</strong></blockquote>
            <ul id="horizonal" style="padding:0;">
                <a class="button" id="addLinkButton">Set link</a>
                <a class="button" href="/">Disconnect</a>
            </ul>
            <figure style="width:100%;text-align:center;">
                ''' + content + '''
            </figure>
            <script>
                document.getElementById("addLinkButton").onclick = showAddLinkForm;
                function showAddLinkForm() {
                    var url = prompt("Link: ")
                    if (url == null||url == "") {
                        return false;
                    }
                    fetch("addLink/''' + token + '''", {
                    method: "POST", 
                    body: JSON.stringify({'url':url})
                    }).then(res => {
                        window.location.reload();
                    });
                    return false;
                }
            </script>
        </body>
    </html>
    '''

@app.route('/addLink/<token>', methods=['POST'])
def AddLink(token):
    data = json.loads(request.data)
    if 'url' not in data:
        return Response(status=400)
    url = data['url']
    url_clean = bleach.clean(str(url))
    global token_cache
    if token != token_cache:
        r = requests.get(f"{ks_apiurl}/{token}/{ks_schemename}")
        if r.status_code!=200:
            return Response(status=400)
        else:
            token_cache = token
    requests.post(f"{ks_apiurl}/{token}/{ks_schemename}", data = json.dumps({"scheme_version":"1", "url":url_clean}))
    return Response(status=200)


@app.route('/fake-kobo-ua')
@app.route('/kobo')
def NewKobo():
    token = GetNewToken()
    return redirect("/kobo/" + token)

@app.route('/kobo/<token>')
def KoboView(token):
    global token_cache
    r = requests.get(f"{ks_apiurl}/{token}/{ks_schemename}")
    if token != token_cache:
        if r.status_code!=200:
            return NewKobo()
        else:
            token_cache = token
    data = r.json()
    if 'url' in data:
        content = bleach.linkify(bleach.clean(str(data['url'])))
    else:
        content = '''<p style="text-align:center">No link saved</p><a class="button" href="javascript:window.location.reload(true)">Refresh</a>'''
    return '''
    <html>
        <head>
            <title>Send to this Kobo</title>
            <link rel="stylesheet" href="/vanilla.css">
            <link rel="stylesheet" href="/style.css">
        </head>
        <body>
            <h1>Send to this Kobo</h1>
            <p>This site makes it easier to access epub download links on your Kobo.</p>
            <blockquote>Access code is <strong class="token">''' + token + '''</strong></blockquote>
            <figure style="width:100%;text-align:center;">
                ''' + content + '''
            </figure>
        </body>
    </html>
    '''

if __name__ == "__main__":
    app.run()