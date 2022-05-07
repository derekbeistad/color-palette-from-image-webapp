import os
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import SubmitField
from werkzeug.utils import secure_filename
import imghdr
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import cv2 as cv
from sklearn.cluster import KMeans
from collections import Counter
import webcolors
from colorthief import ColorThief

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = 'static/img_uploads'
app.config['SECRET_KEY'] = "TOP_SECRET_KEY"


class ImageUploadForm(FlaskForm):
    file = FileField('File')
    submit = SubmitField('Submit')


def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')


@app.route('/', methods=['GET'])
def home():
    form = ImageUploadForm()
    return render_template('index.html', form=form)


@app.route('/', methods=['POST'])
def upload_files():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)
    if filename != '':
        file_ext = os.path.splitext(filename)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS'] or \
                file_ext != validate_image(uploaded_file.stream):
            os.abort(400)
        uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
    return redirect(url_for('palette', img_file_name=filename))


@app.route('/palette/<img_file_name>', methods=['GET', 'POST'])
def palette(img_file_name):
    img_file = url_for('static', filename=f"img_uploads/{img_file_name}")

    im = Image.open(f'static/img_uploads/{img_file_name}')
    image = np.array(im)
    clt = KMeans(n_clusters=10)
    clt_im = clt.fit(image.reshape(-1, 3))
    width = 300
    palette = np.zeros((50, width, 3), np.uint8)
    n_pixels = len(clt_im.labels_)
    counter = Counter(clt_im.labels_)
    perc = {}
    for i in counter:
        perc[i] = np.round(counter[i] / n_pixels, 2)
    perc = dict(sorted(perc.items()))

    print(perc)
    print(clt_im.cluster_centers_)

    step = 0

    for idx, centers in enumerate(clt_im.cluster_centers_):
        palette[:, step:int(step + perc[idx] * width + 1), :] = centers
        step += int(perc[idx] * width + 1)

    palette_img = Image.fromarray(palette)
    palette_img.save(f'static/img_uploads/palette_{img_file_name}')
    palette_path = url_for('static', filename=f"img_uploads/palette_{img_file_name}")
    colors = []
    with open(f'static/img_uploads/palette_{img_file_name}', 'r+b') as f:
        color_thief = ColorThief(f'static/img_uploads/palette_{img_file_name}')
        color_palette = color_thief.get_palette(color_count=10, quality=10)
        for color in color_palette:
            colors.append(webcolors.rgb_to_hex(color))
    return render_template('palette.html', img=img_file, palette=palette_path, colors=colors)


if __name__ == '__main__':
    app.run(debug=True)
