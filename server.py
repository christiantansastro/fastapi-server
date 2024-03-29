import uvicorn
from fastapi import Form, Request, FastAPI
import cv2
import numpy as np
import base64
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000"
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def histogram_equalize(img):
    # split image into bgr channels (blue, green, red - this is the default order for function cv2.split)
    b, g, r = cv2.split(img)
    # carry out histogram equalizaton for each channel
    red = cv2.equalizeHist(r)
    green = cv2.equalizeHist(g)
    blue = cv2.equalizeHist(b)
    return cv2.merge((blue, green, red))  # merge back the three channels


@app.post("/photo")
async def photo(filedata: str = Form(...)):
    image = filedata

    decoded_img = base64.b64decode(image)
    img = Image.open(BytesIO(decoded_img))

    img.save("camera.jpg", "jpeg")

    img_BW = Image.open('camera.jpg')
    img_BW = img_BW.convert('L')
    img_BW.save('imageBW.jpg')

    img_HE = cv2.imread('imageBW.jpg')
    img_HE = histogram_equalize(img_HE)
    cv2.imwrite('imageHE.jpg', img_HE)

    return "success"


@app.get("/process")
async def process():
    img = cv2.imread('imageHE.jpg')

    count = 0
    crop_img = [''] * 5
    coor = [''] * 5

    # threshold on contrast
    lower = np.array([20, 20, 20])
    upper = np.array([50, 50, 50])
    thresh = cv2.inRange(img, lower, upper)

    # apply horizontal morphology
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # get the two largest contours
    contours = cv2.findContours(
        morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]
    # cntrs = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
    cntrs = sorted(contours, key=cv2.contourArea, reverse=True)

    comb = [''] * count
    # get bounding boxes of two largest contours and draw on copy of input
    result = img.copy()
    for i, cntr in enumerate(cntrs[0:10]):
        x, y, w, h = cv2.boundingRect(cntr)
        if (w >= 80 and h >= 80):
            print(i, x, y, w, h)
            coor[i] = [i, x, y, w, h]
            cv2.rectangle(result, (x, y), (x+w, y+h), (0, 0, 255), 2)
            crop_img = img[y:y+h, x:x+w]
            cv2.imwrite("test"+str(i)+'.jpg', crop_img)
            count += 1
            comb.append(coor[i])
    return comb


if __name__ == "__main__":
    uvicorn.run("server:app", host='0.0.0.0', port=10000)
