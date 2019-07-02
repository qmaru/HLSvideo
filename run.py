from flask import Flask, jsonify, render_template, request
from stchannel import STchannelAPI, HLSdownload

api = STchannelAPI()
app = Flask(__name__)


@app.route('/')
def STIndex():
    return render_template('index.html')


@app.route('/api/getlist')
def STList():
    res = request.args
    if res.get("next_id"):
        since_id = res.get("next_id")
        movie_info = api.get_info(since_id)
        movie_urls = api.get_movie_url(movie_info)
        if movie_urls:
            since_id = min(tuple([_["id"] for _ in movie_urls]))
            return jsonify({
                "status": 0,
                "message": "Next data",
                "next_id": since_id,
                "data": movie_urls
            })
        else:
            return jsonify({"status": 1, "message": "No more data"})
    else:
        movie_info = api.get_info()
        movie_urls = api.get_movie_url(movie_info)
        since_id = min(tuple([_["id"] for _ in movie_urls]))
        since_id = min(tuple([_["id"] for _ in movie_urls]))
        return jsonify({
            "status": 0,
            "message": "First data",
            "next_id": since_id,
            "data": movie_urls
        })


@app.route('/api/download', methods=['POST'])
def VideoDownload():
    res = request.json
    murl = res["url"]
    hls = HLSdownload()
    key_video = hls.get_best_info(murl)
    hls.run(key_video)
    return jsonify({"status": 0})


if __name__ == "__main__":
    app.run(debug=True)
