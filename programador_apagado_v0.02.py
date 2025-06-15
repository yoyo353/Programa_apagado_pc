import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys
import json
from datetime import datetime, timedelta

class AutoShutdownApp:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.shutdown_thread = None
        self.is_running = False
        self.config_file = "shutdown_config.json"
        
        # Variables para la interfaz
        self.mode_var = tk.StringVar(value="time")
        self.hour_var = tk.StringVar(value="22")
        self.minute_var = tk.StringVar(value="00")
        self.countdown_hours = tk.StringVar(value="2")
        self.countdown_minutes = tk.StringVar(value="0")
        
        self.create_widgets()
        self.load_config()
        
    def setup_window(self):
        """Configurar la ventana principal"""
        self.root.title("Programador de Apagado")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Hacer que la ventana sea discreta
        self.root.attributes('-topmost', False)
        
        # Protocolo para cerrar la ventana (minimizar a la bandeja del sistema)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
    def create_widgets(self):
        """Crear la interfaz de usuario"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        title_label = ttk.Label(main_frame, text="Programa de Apagado Automático", 
                               font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # Modo de programación
        mode_frame = ttk.LabelFrame(main_frame, text="Modo de Programación", padding="10")
        mode_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="Hora específica", variable=self.mode_var, 
                       value="time", command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Cuenta regresiva", variable=self.mode_var, 
                       value="countdown", command=self.on_mode_change).grid(row=0, column=1, sticky=tk.W)
        
        # Frame para hora específica
        self.time_frame = ttk.LabelFrame(main_frame, text="Programar por Hora", padding="10")
        self.time_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.time_frame, text="Hora:").grid(row=0, column=0, padx=(0, 5))
        hour_combo = ttk.Combobox(self.time_frame, textvariable=self.hour_var, width=5)
        hour_combo['values'] = [f"{i:02d}" for i in range(24)]
        hour_combo.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Label(self.time_frame, text="Minutos:").grid(row=0, column=2, padx=(5, 5))
        minute_combo = ttk.Combobox(self.time_frame, textvariable=self.minute_var, width=5)
        minute_combo['values'] = [f"{i:02d}" for i in range(60)]
        minute_combo.grid(row=0, column=3, padx=(0, 5))
        
        # Frame para cuenta regresiva
        self.countdown_frame = ttk.LabelFrame(main_frame, text="Cuenta Regresiva", padding="10")
        self.countdown_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.countdown_frame, text="Horas:").grid(row=0, column=0, padx=(0, 5))
        hours_combo = ttk.Combobox(self.countdown_frame, textvariable=self.countdown_hours, width=5)
        hours_combo['values'] = [str(i) for i in range(24)]
        hours_combo.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Label(self.countdown_frame, text="Minutos:").grid(row=0, column=2, padx=(5, 5))
        minutes_combo = ttk.Combobox(self.countdown_frame, textvariable=self.countdown_minutes, width=5)
        minutes_combo['values'] = [str(i) for i in range(60)]
        minutes_combo.grid(row=0, column=3, padx=(0, 5))
        
        # Estado actual
        self.status_label = ttk.Label(main_frame, text="Estado: Inactivo", 
                                     font=('Arial', 10))
        self.status_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(15, 0))
        
        self.start_button = ttk.Button(button_frame, text="Iniciar", command=self.start_shutdown_timer)
        self.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Detener", command=self.stop_shutdown_timer, 
                                     state='disabled')
        self.stop_button.grid(row=0, column=1, padx=(5, 5))
        
        ttk.Button(button_frame, text="Minimizar", command=self.minimize_to_tray).grid(row=0, column=2, padx=(5, 0))
        
        self.on_mode_change()
        
    def on_mode_change(self):
        """Cambiar la visibilidad de los frames según el modo seleccionado"""
        if self.mode_var.get() == "time":
            self.time_frame.grid()
            self.countdown_frame.grid_remove()
        else:
            self.time_frame.grid_remove()
            self.countdown_frame.grid()
            
    def start_shutdown_timer(self):
        """Iniciar el temporizador de apagado"""
        if self.is_running:
            return
            
        try:
            if self.mode_var.get() == "time":
                target_time = self.calculate_target_time()
            else:
                target_time = self.calculate_countdown_time()
                
            self.is_running = True
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
            # Iniciar el hilo del temporizador
            self.shutdown_thread = threading.Thread(target=self.shutdown_worker, 
                                                   args=(target_time,), daemon=True)
            self.shutdown_thread.start()
            
            self.save_config()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            
    def calculate_target_time(self):
        """Calcular la hora objetivo para el apagado"""
        now = datetime.now()
        target_hour = int(self.hour_var.get())
        target_minute = int(self.minute_var.get())
        
        target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        # Si la hora objetivo ya pasó hoy, programar para mañana
        if target <= now:
            target += timedelta(days=1)
            
        return target
        
    def calculate_countdown_time(self):
        """Calcular el tiempo objetivo para la cuenta regresiva"""
        hours = int(self.countdown_hours.get())
        minutes = int(self.countdown_minutes.get())
        
        if hours == 0 and minutes == 0:
            raise ValueError("La cuenta regresiva debe ser mayor a 0")
            
        return datetime.now() + timedelta(hours=hours, minutes=minutes)
        
    def shutdown_worker(self, target_time):
        """Hilo trabajador que maneja el temporizador"""
        try:
            while self.is_running and datetime.now() < target_time:
                remaining = target_time - datetime.now()
                
                if remaining.total_seconds() <= 0:
                    break
                    
                # Actualizar el estado en la interfaz
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                status_text = f"Apagado en: {hours:02d}:{minutes:02d}:{seconds:02d}"
                self.root.after(0, lambda: self.status_label.config(text=status_text))
                
                time.sleep(1)
                
            if self.is_running:
                # Mostrar advertencia antes de apagar
                self.root.after(0, self.show_shutdown_warning)
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error en el temporizador: {e}"))
            self.root.after(0, self.stop_shutdown_timer)
            
    def show_shutdown_warning(self):
        """Mostrar advertencia de apagado inminente (no bloqueante)"""
        # Crear ventana de advertencia no bloqueante
        warning_window = tk.Toplevel(self.root)
        warning_window.title("¡Apagado Programado!")
        warning_window.geometry("350x150")
        warning_window.resizable(False, False)
        warning_window.attributes('-topmost', True)
        
        # Centrar la ventana
        warning_window.transient(self.root)
        warning_window.grab_set()
        
        # Contenido de la ventana de advertencia
        frame = ttk.Frame(warning_window, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="⚠️ APAGADO PROGRAMADO ⚠️", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        self.warning_label = ttk.Label(frame, text="El sistema se apagará en 30 segundos", 
                                      font=('Arial', 10))
        self.warning_label.pack(pady=(0, 15))
        
        # Botón para cancelar
        cancel_button = ttk.Button(frame, text="CANCELAR APAGADO", 
                                  command=lambda: self.cancel_from_warning(warning_window))
        cancel_button.pack()
        
        # Iniciar cuenta regresiva de 30 segundos INMEDIATAMENTE
        threading.Thread(target=self.final_countdown, args=(warning_window,), daemon=True).start()
            
    def final_countdown(self, warning_window=None):
        """Cuenta regresiva final antes del apagado"""
        for i in range(30, 0, -1):
            if not self.is_running:
                if warning_window and warning_window.winfo_exists():
                    warning_window.destroy()
                return
                
            # Actualizar tanto la ventana principal como la de advertencia
            status_text = f"Apagando en {i} segundos..."
            self.root.after(0, lambda: self.status_label.config(text=status_text))
            
            if warning_window and warning_window.winfo_exists():
                warning_text = f"El sistema se apagará en {i} segundos"
                try:
                    self.root.after(0, lambda txt=warning_text: self.warning_label.config(text=txt))
                except:
                    pass  # La ventana podría haber sido cerrada
                    
            time.sleep(1)
            
        # Si llegamos aquí, ejecutar el apagado
        if self.is_running:
            if warning_window and warning_window.winfo_exists():
                warning_window.destroy()
            self.shutdown_system()
            
    def cancel_from_warning(self, warning_window):
        """Cancelar apagado desde la ventana de advertencia"""
        self.stop_shutdown_timer()
        warning_window.destroy()
            
    def shutdown_system(self):
        """Ejecutar el apagado del sistema"""
        try:
            # Comando para apagar Windows
            os.system("shutdown /s /t 0")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo apagar el sistema: {e}"))
            
    def stop_shutdown_timer(self):
        """Detener el temporizador de apagado"""
        self.is_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="Estado: Detenido")
        
    def minimize_to_tray(self):
        """Minimizar la ventana (simular bandeja del sistema)"""
        self.root.withdraw()  # Ocultar la ventana
        
        # En una implementación completa, aquí se agregaría a la bandeja del sistema
        # Por simplicidad, mostraremos un mensaje
        print("Aplicación minimizada. Ejecute el archivo nuevamente para mostrar la ventana.")
        
    def save_config(self):
        """Guardar la configuración actual"""
        config = {
            'mode': self.mode_var.get(),
            'hour': self.hour_var.get(),
            'minute': self.minute_var.get(),
            'countdown_hours': self.countdown_hours.get(),
            'countdown_minutes': self.countdown_minutes.get()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass  # Ignorar errores de guardado
            
    def load_config(self):
        """Cargar configuración guardada"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            self.mode_var.set(config.get('mode', 'time'))
            self.hour_var.set(config.get('hour', '22'))
            self.minute_var.set(config.get('minute', '00'))
            self.countdown_hours.set(config.get('countdown_hours', '2'))
            self.countdown_minutes.set(config.get('countdown_minutes', '0'))
            
            self.on_mode_change()
            
        except Exception:
            pass  # Usar valores por defecto si no se puede cargar
            
    def run(self):
        """Ejecutar la aplicación"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AutoShutdownApp()
    app.run()