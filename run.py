from flask import Flask, jsonify, render_template, request
from stchannel import STchannelAPI, HLSdownload

api = STchannelAPI()
hls = HLSdownload()

app = Flask(__name__)


@app.route('/')
def STIndex():
    return render_template('index.html')


@app.route('/api/getlist')
def STList():
    movie_info = api.get_info()
    movie_urls = api.get_movie_url(movie_info)
    return jsonify(movie_urls)


@app.route('/api/download', methods=['POST'])
def VideoDownload():
    res = request.json
    murl = res["url"]
    key_video = hls.get_best_info(murl)
    hls.run(key_video)
    return jsonify({"status": 0})


if __name__ == "__main__":
    app.run(debug=True)
