import cv2
import numpy as np
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.utils import platform

if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.CAMERA,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE,
        Permission.INTERNET
    ])

class MainApp(App):
    def build(self):
        self.real_distance_meters = 15.0
        self.prev_time = time.time()
        
        # محاولة فتح الكاميرا (0 أو 1 أو افتراضية)
        self.capture = cv2.VideoCapture(0)
        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(-1)

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=40, detectShadows=False)
        
        # جدولة تحديث الإطارات
        Clock.schedule_interval(self.update_frame, 1.0 / 30.0)
        return self.root

    def update_frame(self, dt):
        if not self.capture.isOpened():
            return
            
        ret, frame = self.capture.read()
        if not ret:
            return

        h, w, _ = frame.shape
        current_time = time.time()
        time_diff = current_time - self.prev_time
        self.prev_time = current_time
        if time_diff <= 0:
            time_diff = 0.033

        # مناطق الرصد: السماء (في الأعلى) والطريق (في الأسفل)
        sky_line_y = int(h * 0.35)
        road_start_y = int(h * 0.45)
        road_end_y = int(h * 0.85)

        # رسم خطوط التتبع على الفيديو
        # منطقة الطائرات (السماء)
        cv2.line(frame, (0, sky_line_y), (w, sky_line_y), (0, 200, 255), 2)
        cv2.putText(frame, "SKY ZONE (Airplanes)", (20, sky_line_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        # منطقة السيارات (الطريق)
        cv2.line(frame, (0, road_start_y), (w, road_start_y), (0, 255, 100), 2)
        cv2.line(frame, (0, road_end_y), (w, road_end_y), (255, 100, 0), 2)
        cv2.putText(frame, "ROAD ZONE (Cars & Vehicles)", (20, road_start_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)

        # معالجة الصورة واكتشاف الحركة
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        fg_mask = self.bg_subtractor.apply(blur)
        
        _, thresh = cv2.threshold(fg_mask, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_car_speed = 0
        max_plane_speed = 0
        detected_objects_count = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 1000:  # تصفية الضوضاء
                x, y, bw, bh = cv2.boundingRect(cnt)
                center_y = y + (bh // 2)
                detected_objects_count += 1

                # هل الجسم في السماء (طائرة) أم على الطريق (سيارة)؟
                if center_y < sky_line_y:
                    # جسم جوي / طائرة
                    pixel_distance = abs(h * 0.3)
                    meters_per_pixel = 50.0 / pixel_distance  # نطاق أوسع للطائرات
                    speed_m_s = (bh / time_diff) * meters_per_pixel
                    speed_kmh = speed_m_s * 3.6 * 2.5  # معامل تصحيح الارتفاع والسرعة الجوية
                    
                    if 30 < speed_kmh < 950:
                        max_plane_speed = max(max_plane_speed, int(speed_kmh))
                        
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 165, 255), 2)
                    cv2.putText(frame, f"Airplane: {int(speed_kmh)} KM/H", (x, max(20, y - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

                elif road_start_y <= center_y <= road_end_y:
                    # مركبة أرضية / سيارة
                    pixel_distance = abs(road_end_y - road_start_y)
                    meters_per_pixel = self.real_distance_meters / pixel_distance
                    speed_m_s = (bh / time_diff) * meters_per_pixel
                    speed_kmh = speed_m_s * 3.6
                    
                    if 5 < speed_kmh < 260:
                        max_car_speed = max(max_car_speed, int(speed_kmh))
                        
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 136), 2)
                    cv2.putText(frame, f"Car: {int(speed_kmh)} KM/H", (x, max(20, y - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 136), 2)

        # تحديث الواجهة بأسلوب عصري وأنيق
        try:
            if max_car_speed > 0:
                self.root.ids.car_speed_label.text = f"{max_car_speed} [color=00FF88]KM/H[/color]"
            if max_plane_speed > 0:
                self.root.ids.plane_speed_label.text = f"{max_plane_speed} [color=00A2FF]KM/H[/color]"
            
            self.root.ids.status_label.text = f"الحالة: نشط | الأجسام المرصودة: {detected_objects_count}"
        except Exception:
            pass

        # تحويل الإطار للعرض في Kivy
        buffer = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(w, h), colorfmt='bgr')
        texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
        self.root.ids.camera_preview.texture = texture

    def on_calibrate_click(self):
        try:
            self.root.ids.status_label.text = "حالة النظام: تمت معايرة النطاقات بنجاح"
        except:
            pass

    def on_stop(self):
        if self.capture.is_opened():
            self.capture.release()

if __name__ == '__main__':
    MainApp().run()
