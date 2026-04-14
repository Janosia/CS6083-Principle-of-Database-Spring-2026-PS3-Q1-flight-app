from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",   
    "user": "postgres",       
    "password": "Janosia"   
}

def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()
    cur.execute("SET search_path TO flight")
    return conn
app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'flights.db')

@app.route('/')
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT airport_code, name, city, country FROM public.airport ORDER BY airport_code")
    airports=cur.fetchall()
    conn.close()
    return render_template('index.html', airports=airports)

@app.route('/search', methods=['GET'])
def search():
    origin = request.args.get('origin', '').strip().upper()
    dest = request.args.get('dest', '').strip().upper()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    if not origin or not dest or not date_from or not date_to:
        return render_template('index.html', error="Please fill in all fields.")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            f.flight_number,
            f.departure_date,
            fs.airline_name,
            fs.origin_code,
            fs.dest_code,
            a1.city AS origin_city,
            a2.city AS dest_city,
            fs.departure_time,
            fs.duration,
            f.plane_type
        FROM public.flight f
        JOIN public.flightservice fs ON f.flight_number = fs.flight_number
        JOIN public.airport a1 ON fs.origin_code = a1.airport_code
        JOIN public.airport a2 ON fs.dest_code = a2.airport_code
        WHERE fs.origin_code = %s
          AND fs.dest_code = %s
          AND f.departure_date BETWEEN %s AND %s
        ORDER BY f.departure_date, fs.departure_time,  fs.airline_name
    """, (origin, dest, date_from, date_to))
    flights = cur.fetchall()
    conn.close()

    return render_template('results.html',flights=flights, origin=origin, dest=dest, date_from=date_from, date_to=date_to)

@app.route('/flight/<flight_number>/<date>')
def flight_detail(flight_number, date):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            f.flight_number,
            f.departure_date,
            f.plane_type,
            fs.airline_name,
            fs.origin_code,
            fs.dest_code,
            a1.name AS origin_name,
            a1.city AS origin_city,
            a2.name AS dest_name,
            a2.city AS dest_city,
            fs.departure_time,
            fs.duration,
            ac.capacity,
            COUNT(b.pid) AS booked_seats
        FROM public.flight f
        JOIN public.flightservice fs ON f.flight_number = fs.flight_number
        JOIN public.airport a1 ON fs.origin_code = a1.airport_code
        JOIN public.airport a2 ON fs.dest_code = a2.airport_code
        JOIN public.aircraft ac ON f.plane_type = ac.plane_type
        LEFT JOIN public.booking b ON b.flight_number = f.flight_number AND b.departure_date = f.departure_date
        WHERE f.flight_number = %s AND f.departure_date = %s
        GROUP BY f.flight_number, f.departure_date, f.plane_type,
            fs.airline_name,
            fs.origin_code,
            fs.dest_code,
            a1.name ,
            a1.city,
            a2.name,
            a2.city ,
            fs.departure_time,
            fs.duration,
            ac.capacity
    """, (flight_number, date))
    detail = cur.fetchone()

    cur.execute("""
        SELECT b.seat_number, p.passenger_name
        FROM public.booking b
        JOIN public.passenger p ON b.pid = p.pid
        WHERE b.flight_number = %s AND b.departure_date = %s
        ORDER BY b.seat_number
    """, (flight_number, date))
    bookings = cur.fetchall()

    conn.close()

    if not detail:
        return "Flight not found", 404

    return render_template('detail.html', flight=detail, bookings=bookings)

if __name__ == '__main__':
    app.run(debug=True, port=5050)
