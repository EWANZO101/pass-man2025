from flask import Flask, render_template, request, redirect, flash, jsonify
import subprocess
import psutil
import platform
import socket
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_should_be_strong_and_secret'

# System information functions
def get_system_info():
    return {
        'system': platform.system(),
        'node': platform.node(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
        'ip_address': socket.gethostbyname(socket.gethostname())
    }

def get_users():
    try:
        result = subprocess.run(['net', 'user'], capture_output=True, text=True, check=True)
        users = [line.strip() for line in result.stdout.split('\n') if line.strip() and not line.startswith('--')]
        return users[4:-2] if len(users) > 6 else users
    except subprocess.CalledProcessError:
        return []

# Routes
@app.route('/')
def index():
    return render_template('index.html', system_info=get_system_info())

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match!", 'error')
            return redirect('/reset_password')

        try:
            subprocess.run(['net', 'user', username, new_password], check=True)
            flash(f"Password for {username} reset successfully!", 'success')
        except subprocess.CalledProcessError as e:
            flash(f"Failed to reset password: {str(e)}", 'error')
        return redirect('/reset_password')
    
    return render_template('reset_password.html', users=get_users())

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        permissions = request.form.getlist('permissions')

        if new_password != confirm_password:
            flash("Passwords do not match!", 'error')
            return redirect('/create_user')

        try:
            # Create user
            subprocess.run(['net', 'user', new_username, new_password, '/add'], check=True)
            
            # Add to groups
            for permission in permissions:
                subprocess.run(['net', 'localgroup', permission, new_username, '/add'], check=True)
            
            flash(f"User {new_username} created successfully!", 'success')
        except subprocess.CalledProcessError as e:
            flash(f"Failed to create user: {str(e)}", 'error')
        return redirect('/create_user')

    return render_template('create_user.html')

@app.route('/manage_users')
def manage_users():
    users = get_users()
    user_details = []
    
    for user in users:
        try:
            result = subprocess.run(['net', 'user', user], capture_output=True, text=True, check=True)
            user_details.append({
                'name': user,
                'details': result.stdout
            })
        except subprocess.CalledProcessError:
            continue
    
    return render_template('manage_users.html', users=user_details)

@app.route('/system_commands', methods=['GET', 'POST'])
def system_commands():
    if request.method == 'POST':
        command = request.form.get('command')
        
        if command == 'shutdown':
            try:
                subprocess.run(['shutdown', '/s', '/t', '60'], check=True)
                flash("System will shutdown in 1 minute", 'success')
            except subprocess.CalledProcessError as e:
                flash(f"Failed to execute shutdown: {str(e)}", 'error')
        elif command == 'restart':
            try:
                subprocess.run(['shutdown', '/r', '/t', '60'], check=True)
                flash("System will restart in 1 minute", 'success')
            except subprocess.CalledProcessError as e:
                flash(f"Failed to execute restart: {str(e)}", 'error')
        elif command == 'cancel':
            try:
                subprocess.run(['shutdown', '/a'], check=True)
                flash("Pending shutdown/restart cancelled", 'success')
            except subprocess.CalledProcessError as e:
                flash(f"Failed to cancel operation: {str(e)}", 'error')
        
        return redirect('/system_commands')
    
    return render_template('system_commands.html')

@app.route('/processes')
def processes():
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            processes.append(proc.info)
        return render_template('processes.html', processes=processes)
    except Exception as e:
        flash(f"Failed to get processes: {str(e)}", 'error')
        return redirect('/')

@app.route('/kill_process', methods=['POST'])
def kill_process():
    pid = request.form.get('pid')
    try:
        p = psutil.Process(int(pid))
        p.terminate()
        return jsonify({'success': True, 'message': f'Process {pid} terminated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/disk_management')
def disk_management():
    try:
        disks = []
        for partition in psutil.disk_partitions():
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            })
        return render_template('disk_management.html', disks=disks)
    except Exception as e:
        flash(f"Failed to get disk information: {str(e)}", 'error')
        return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
