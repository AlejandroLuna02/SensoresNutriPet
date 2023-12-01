import tkinter as tk
from tkinter import Label
import Adafruit_DHT
import time
from datetime import datetime
import RPi.GPIO as GPIO
from threading import Thread
import requests

sensor = Adafruit_DHT.DHT11
pin_sensor = 4

TRIG = 23
ECHO = 24
servoPIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(servoPIN, GPIO.OUT)

mensaje_label = None
temperatura_global = 0
humedad_global = 0
distancia_global = 0

api_url = "http://54.147.241.142:9000/api/CreateDatos"  # Ajusta la ruta según tu API

horas_deseadas = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:17", "20:00", "22:00"]

def enviar_datos_a_api(temperatura, humedad, distancia, mensaje_comedero):
    while True:
        ahora = datetime.now()
        hora_actual = ahora.strftime("%H:%M")
#          print("Hora Actual: " + hora_actual)

        json_data = {
            "temperatura": temperatura,
            "humedad": humedad,
            "distancia": distancia,
            "mensaje": mensaje_comedero,
            "hora": "18:00"
        }

        # Realiza la solicitud POST
        response = requests.post(api_url, json=json_data)

        # Imprime la respuesta
#         print(response.text)

        if response.status_code == 200:  # Verifica si la solicitud fue exitosa
            print("Datos enviados exitosamente a la API.")
            mensaje_enviado_label.config(text="Datos enviados a la API correctamente")

        if hora_actual in horas_deseadas:
            json_data = {
                'temperatura': temperatura,
                'humedad': humedad,
                'distancia': distancia,
                'mensaje': mensaje_comedero,
                'hora': hora_actual
            }

            # Realiza la solicitud POST
            response = requests.post('http://54.147.241.142:9000/api/CreateDatosHora', json=json_data)

            # Imprime la respuesta
#             print(response.text)
            
            if response.status_code == 200:  # Verifica si la solicitud fue exitosa
                print("Datos enviados exitosamente a la API.")
                mensaje_enviado_label.config(text="Datos enviados a la API correctamente")

            time.sleep(60)
        else:
            time.sleep(2)

def read_sensor_data():
    global temperatura_global, humedad_global, distancia_global
    
    humedad, temperatura = Adafruit_DHT.read_retry(sensor, pin_sensor)

    if humedad is not None and temperatura is not None:
        temperatura_str = 'Temp={0:0.1f}*C'.format(temperatura)
        humedad_str = 'Humedad={0:0.1f}%'.format(humedad)
        distancia_str = 'Distancia={0:.2f} cm'.format(distancia_global)

        info_str = f"{temperatura_str}, {humedad_str}, {distancia_str}"

        temperatura_label.config(text=info_str)

        temperatura_global = temperatura
        humedad_global = humedad

        # Mueve el servo en función de la distancia
        mover_servo(distancia_global)

        # Enviar datos a la API cada dos horas
        now = datetime.now()
        if now.hour % 2 == 0 and now.minute == 0:
            enviar_datos_a_api(temperatura_global, humedad_global, distancia_global, mensaje_comedero)

    else:
        temperatura_label.config(text='Hubo un fallo al leer del sensor. ¡Inténtalo de nuevo!')

    root.after(2000, read_sensor_data)

def ultrasonico_measurement():
    global distancia_global, mensaje_comedero
    
    distancia_global = 0
    mensaje_comedero = ""

    try:
        while True:
            GPIO.output(TRIG, GPIO.LOW)
            time.sleep(2)

            GPIO.output(TRIG, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(TRIG, GPIO.LOW)

            pulso_inicio = time.time()
            while GPIO.input(ECHO) == GPIO.LOW:
                pass

            pulso_fin = time.time()
            while GPIO.input(ECHO) == GPIO.HIGH:
                pass

            duracion = pulso_fin - pulso_inicio
            distancia = (34300 * duracion) / 2

            if distancia < 15:
                mensaje_comedero = "El comedero está lleno."
            elif distancia > 16:
                mensaje_comedero = "El comedero se está vaciando."

            # Actualizar el mensaje_label en el hilo principal
            root.after(0, lambda: mensaje_label.config(text=mensaje_comedero))

            distancia_global = distancia

            enviar_datos_a_api(temperatura_global, humedad_global, distancia_global, mensaje_comedero)

            time.sleep(2)

    finally:
        GPIO.cleanup()

def mover_servo(distancia):
    # Lógica para mover el servo en función de la distancia
    # Ajusta esto según tus necesidades
    if distancia < 10:
        p.ChangeDutyCycle(2.5)  # Gira a 0 grados
    elif 10 <= distancia < 20:
        p.ChangeDutyCycle(7.5)  # Gira a 90 grados (posición central)
    else:
        p.ChangeDutyCycle(12.5)  # Gira a 180 grados

    # Programa el próximo movimiento del servo en el hilo principal
    root.after(2 * 60 * 60 * 1000, lambda: mover_servo(distancia_global))

# Configurar el PWM para el servo
p = GPIO.PWM(servoPIN, 50)  # GPIO 18 for PWM with 50Hz
p.start(7.5)  # Establece el ciclo de trabajo para la posición central (90 grados)

ultrasonico_thread = Thread(target=ultrasonico_measurement)

root = tk.Tk()
root.title("Datos del Sensor DHT11 y Sensor Ultrasonico")

temperatura_label = Label(root, text="")
temperatura_label.pack()

mensaje_label = Label(root, text="")
mensaje_label.pack()

mensaje_enviado_label = Label(root, text="")
mensaje_enviado_label.pack()

root.after(0, read_sensor_data)
ultrasonico_thread.start()

root.mainloop()