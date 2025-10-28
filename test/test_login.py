import pytest  # testframework waarmee je eenvoudig testfuncties kunt schrijven en uitvoeren.
import requests  # library om HTTP-verzoeken te versturen naar een server.

# User login
def test_valid_login():
    data = {"username": "testuser", "password": "testuser123"}
    url = "http://localhost:8000/login"
    res = requests.post(url, json=data)

    assert res.status_code == 200
    assert res.json()["message"] == "User logged in"


def test_wrong_password():
    data = {"username": "testuser", "password": "123testuser"}
    url = "http://localhost:8000/login"
    res = requests.post(url, json=data)

    assert res.status_code == 401
    assert res.text == "Invalid credentials"


def test_login_empty_body():
    url = "http://localhost:8000/login"
    res = requests.post(url)

    assert res.status_code == 400
    assert res.text == "Empty request body"