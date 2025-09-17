from app import app  # Importa tu aplicación Flask
from vercel.request import Request
from vercel.response import Response

def handler(request: Request, response: Response):
    # Esta función actuará como wrapper para tu app Flask
    response.status = 200
    response.send("Aplicación funcionando en Vercel")