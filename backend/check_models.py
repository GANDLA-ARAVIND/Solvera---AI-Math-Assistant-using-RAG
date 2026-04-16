import google.generativeai as genai

genai.configure(api_key='AIzaSyA5zwkWQBdsUgwdmnwCGI0Uuir1XqQlv6U')

try:
    models = genai.list_models()
    print("Available models:")
    for m in models:
        print(f"  {m.name}")
except Exception as e:
    print(f"Error: {e}")
