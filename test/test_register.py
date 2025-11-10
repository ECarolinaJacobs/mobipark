import pytest  # testframework waarmee je eenvoudig testfuncties kunt schrijven en uitvoeren.
import requests  # library om HTTP-verzoeken te versturen naar een server.


# User registering
def test_create_new_account():
    data = {"username": "testuser", "password": "testuser123", "name": "Test User"}
    url = "http://localhost:8000/register"
    res = requests.post(url, json=data)

    assert res.status_code == 201
    assert res.text == "User created"


def test_account_exists():
    data = {"username": "testuser", "password": "testuser123", "name": "Test User"}
    url = "http://localhost:8000/register"
    res = requests.post(url, json=data)

    assert res.status_code == 409
    assert res.text == "Username already taken"


def test_empty_body():
    url = "http://localhost:8000/register"
    res = requests.post(url)

    assert res.status_code == 400
    assert res.text == "Invalid or empty request body"


def test_missing_fields():
    data = {}
    url = "http://localhost:8000/register"
    res = requests.post(url, json=data)

    assert res.status_code == 400
    assert res.text == "Missing fields"