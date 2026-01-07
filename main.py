from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.video import Video
import supabase
from supabase import create_client, Client
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFlatButton, MDRectangleFlatIconButton
from kivymd.uix.list import TwoLineAvatarListItem, IconLeftWidget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.chip import MDChip
from kivy.uix.image import AsyncImage

import uuid
import os
import threading
import re
from datetime import datetime, timedelta, timezone
import json

# --- SUPABASE BAĞLANTISI ---
URL = "https://bkmvtjwpwkouyjjdivhi.supabase.co"
KEY = "sb_publishable_2qT-exkQbtG6J-WbPiNbnQ_ZXQsDimQ"
vibe_db: Client = create_client(URL, KEY)

Window.size = (360, 640)


# --- YARDIMCI FONKSİYONLAR ---
def show_snackbar(message, success=True):
    """Snackbar göstermek için yardımcı fonksiyon"""
    snackbar = Snackbar(
        MDLabel(text=message),
        duration=2,
        bg_color=(0.2, 0.7, 0.3, 1) if success else (0.9, 0.3, 0.3, 1)
    )
    snackbar.open()


def validate_email(email):
    """Email formatını kontrol et"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Şifre güçlü mü kontrol et (en az 6 karakter)"""
    return len(password) >= 6


class LoadingScreen(Screen):
    """Yükleniyor ekranı"""
    pass


# --- EKRAN SINIFLARI ---
class LoginScreen(Screen):
    reset_dialog = None

    def login_user(self):
        email = self.ids.email.text.strip()
        password = self.ids.password.text.strip()

        # Validasyon
        if not email or not password:
            show_snackbar("Lütfen tüm alanları doldurun", False)
            return

        if not validate_email(email):
            show_snackbar("Geçerli bir email adresi girin", False)
            return

        # Loading göster
        self.manager.current = "loading"

        try:
            auth = vibe_db.auth.sign_in_with_password(
                {"email": email, "password": password})

            # Kullanıcı bilgilerini al
            p = vibe_db.table("profiles").select("username").eq("id", auth.user.id).single().execute().data
            MDApp.get_running_app().user_data["username"] = p["username"] if p else "User"
            MDApp.get_running_app().user_data["user_id"] = auth.user.id

            # Dark mode ayarını yükle
            self.load_theme_preference(auth.user.id)

            self.manager.current = "main"
            show_snackbar("Giriş başarılı!")

        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg:
                show_snackbar("Email veya şifre hatalı", False)
            elif "not found" in error_msg:
                show_snackbar("Kullanıcı bulunamadı", False)
            else:
                show_snackbar("Giriş hatası: " + str(e)[:50], False)
            self.manager.current = "login"

    def load_theme_preference(self, user_id):
        """Kullanıcının tema tercihini yükle"""
        try:
            app = MDApp.get_running_app()
            prefs = vibe_db.table("user_preferences").select("dark_mode").eq("user_id", user_id).execute()
            if prefs.data:
                app.theme_cls.theme_style = "Dark" if prefs.data[0]['dark_mode'] else "Light"
        except:
            pass

    def open_reset_dialog(self):
        """Şifre sıfırlama dialogu"""
        content = MDBoxLayout(
            orientation="vertical",
            spacing="12dp",
            size_hint_y=None,
            height="120dp"
        )

        self.reset_email = MDTextField(
            hint_text="Kayıtlı email adresiniz",
            mode="fill"
        )
        content.add_widget(self.reset_email)

        self.reset_dialog = MDDialog(
            title="🔐 Şifremi Unuttum",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="İptal",
                    on_release=lambda x: self.reset_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Gönder",
                    on_release=lambda x: self.send_reset_email()
                )
            ]
        )
        self.reset_dialog.open()

    def send_reset_email(self):
        """Şifre sıfırlama emaili gönder"""
        email = self.reset_email.text.strip()

        if not email:
            show_snackbar("Lütfen email adresinizi girin", False)
            return

        if not validate_email(email):
            show_snackbar("Geçerli bir email adresi girin", False)
            return

        try:
            vibe_db.auth.reset_password_for_email(email)
            self.reset_dialog.dismiss()
            show_snackbar("Şifre sıfırlama linki emailinize gönderildi!")
        except Exception as e:
            show_snackbar(f"Hata: {str(e)[:50]}", False)


class SignupScreen(Screen):
    def signup_user(self):
        email = self.ids.new_email.text.strip()
        password = self.ids.new_password.text.strip()

        # Validasyon
        if not email or not password:
            show_snackbar("Lütfen tüm alanları doldurun", False)
            return

        if not validate_email(email):
            show_snackbar("Geçerli bir email adresi girin", False)
            return

        if not validate_password(password):
            show_snackbar("Şifre en az 6 karakter olmalı", False)
            return

        try:
            vibe_db.auth.sign_up({"email": email, "password": password})
            show_snackbar("Kayıt başarılı! Kullanıcı adınızı belirleyin.")
            self.manager.current = "username"
        except Exception as e:
            error_msg = str(e).lower()
            if "already" in error_msg:
                show_snackbar("Bu email adresi zaten kayıtlı", False)
            else:
                show_snackbar(f"Kayıt hatası: {str(e)[:50]}", False)


class UsernameScreen(Screen):
    def save_username(self):
        username = self.ids.username_input.text.strip()

        if not username:
            show_snackbar("Lütfen kullanıcı adı girin", False)
            return

        if len(username) < 3:
            show_snackbar("Kullanıcı adı en az 3 karakter olmalı", False)
            return

        MDApp.get_running_app().user_data["username"] = username
        self.manager.current = "birthdate"


class BirthDateScreen(Screen):
    def show_date_picker(self):
        picker = MDDatePicker()
        picker.bind(on_save=self.on_save)
        picker.open()

    def on_save(self, instance, value, date_range):
        self.ids.selected_date_label.text = str(value)
        MDApp.get_running_app().user_data["birthdate"] = str(value)

    def finish_onboarding(self):
        user = vibe_db.auth.get_user().user
        user_data = MDApp.get_running_app().user_data

        if not user_data.get("birthdate"):
            show_snackbar("Lütfen doğum tarihinizi seçin", False)
            return

        try:
            # Profili oluştur
            vibe_db.table("profiles").upsert({
                "id": user.id,
                "username": user_data["username"],
                "birth_date": user_data["birthdate"]
            }).execute()

            # Varsayılan tercihleri oluştur
            vibe_db.table("user_preferences").insert({
                "user_id": user.id,
                "dark_mode": False,
                "notifications": True
            }).execute()

            show_snackbar("Profil oluşturuldu!")
            self.manager.current = "main"
        except Exception as e:
            show_snackbar(f"Hata: {str(e)[:50]}", False)


class MainScreen(Screen):
    comment_dialog = None
    story_dialog = None
    file_manager = None
    loading = False
    refresh_trigger = None

    def on_enter(self):
        u_name = MDApp.get_running_app().user_data.get("username", "Kullanıcı")
        self.ids.welcome_msg.text = f"Hoş geldin, {u_name}!"
        self.load_posts()
        self.load_stories_preview()
        self.update_notification_count()

        # 30 saniyede bir feed'i yenile
        Clock.schedule_interval(self.refresh_feed, 30)

    def on_leave(self):
        Clock.unschedule(self.refresh_feed)
        if self.refresh_trigger:
            self.refresh_trigger.cancel()

    def refresh_feed(self, dt):
        """Feed'i yenile"""
        self.load_posts()
        self.load_stories_preview()
        self.update_notification_count()

    def on_scroll_stop(self, *args):
        """Swipe to refresh kontrolü"""
        if self.ids.scroll_view.scroll_y >= 1.0 and not self.loading:
            self.refresh_trigger = Clock.schedule_once(lambda dt: self.manual_refresh(), 0.5)

    def manual_refresh(self):
        """Manuel refresh"""
        self.loading = True
        self.ids.refresh_spinner.active = True
        self.load_posts()
        self.load_stories_preview()
        Clock.schedule_once(lambda dt: self.stop_refresh_spinner(), 1)

    def stop_refresh_spinner(self):
        """Refresh spinner'ı durdur"""
        self.loading = False
        self.ids.refresh_spinner.active = False
        show_snackbar("Feed yenilendi!")

    def update_notification_count(self):
        """Bildirim sayısını güncelle"""
        try:
            my_id = MDApp.get_running_app().user_data.get("user_id")
            if not my_id:
                return

            # Okunmamış mesaj sayısı
            unread_msgs = vibe_db.table("messages").select("id", count="exact").eq(
                "room_id", "TODO").eq("read", False).execute().count

            # Okunmamış beğeni sayısı
            unread_likes = vibe_db.table("notifications").select("id", count="exact").eq(
                "user_id", my_id).eq("read", False).eq("type", "like").execute().count

            total = unread_msgs + unread_likes
            if total > 0:
                self.ids.notification_badge.text = str(total) if total < 10 else "9+"
                self.ids.notification_badge.opacity = 1
            else:
                self.ids.notification_badge.opacity = 0

        except:
            self.ids.notification_badge.opacity = 0

    def load_stories_preview(self):
        try:
            my_id = vibe_db.auth.get_user().user.id
            time_limit = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

            follows = vibe_db.table("follows").select("followed_id").eq("follower_id", my_id).execute()
            followed_ids = [f["followed_id"] for f in follows.data]
            followed_ids.append(my_id)

            stories = vibe_db.table("stories").select("*, profiles(username)").in_("user_id", followed_ids).gte(
                "created_at", time_limit).execute().data

            self.ids.stories_container.clear_widgets()

            # Kendi hikaye ekleme butonu
            add_btn = MDIconButton(
                icon="plus-circle-outline",
                theme_text_color="Primary",
                on_release=lambda x: self.open_story_creator(),
                size_hint=(None, None),
                size=("60dp", "60dp")
            )
            self.ids.stories_container.add_widget(add_btn)

            # Hikayeleri ekle
            for story in stories[:6]:
                btn = MDIconButton(
                    icon="circle",
                    theme_text_color="Custom",
                    text_color=(0.2, 0.6, 1, 1),
                    on_release=lambda x, s=story: self.view_story(s),
                    size_hint=(None, None),
                    size=("60dp", "60dp")
                )
                self.ids.stories_container.add_widget(btn)

        except Exception as e:
            print(f"Hikaye önizleme hatası: {e}")

    def open_story_creator(self):
        content = MDBoxLayout(orientation="vertical", spacing="20dp", size_hint_y=None, height="250dp")

        self.story_caption = MDTextField(hint_text="Hikaye açıklaması (opsiyonel)")
        content.add_widget(self.story_caption)

        btn_box = MDBoxLayout(spacing="10dp")

        photo_btn = MDRaisedButton(
            text="📷 Fotoğraf",
            size_hint=(0.5, None),
            height="40dp",
            on_release=lambda x: self.select_story_photo()
        )

        video_btn = MDRaisedButton(
            text="🎥 Video",
            size_hint=(0.5, None),
            height="40dp",
            on_release=lambda x: self.select_story_video()
        )

        btn_box.add_widget(photo_btn)
        btn_box.add_widget(video_btn)
        content.add_widget(btn_box)

        self.story_dialog = MDDialog(
            title="Hikaye Oluştur",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="İptal", on_release=lambda x: self.story_dialog.dismiss()),
                MDRaisedButton(text="Paylaş", on_release=lambda x: self.upload_story())
            ]
        )
        self.story_dialog.open()

    def select_story_photo(self):
        app = MDApp.get_running_app()
        app.current_screen = self
        app.file_manager = MDFileManager(
            exit_manager=app.exit_manager,
            select_path=lambda path: self.set_story_media(path, 'image'),
            preview=True
        )
        app.file_manager.show('/')

    def select_story_video(self):
        app = MDApp.get_running_app()
        app.current_screen = self
        app.file_manager = MDFileManager(
            exit_manager=app.exit_manager,
            select_path=lambda path: self.set_story_media(path, 'video'),
            preview=True
        )
        app.file_manager.show('/')

    def set_story_media(self, path, media_type):
        self.selected_story_path = path
        self.selected_story_type = media_type
        self.story_dialog.dismiss()
        self.upload_story()

    def upload_story(self):
        if hasattr(self, 'selected_story_path'):
            try:
                # Loading göster
                self.ids.loading_spinner.active = True

                file_name = f"{uuid.uuid4()}_{os.path.basename(self.selected_story_path)}"
                bucket = "stories"

                with open(self.selected_story_path, 'rb') as f:
                    vibe_db.storage.from_(bucket).upload(
                        file=self.selected_story_path,
                        path=file_name,
                        file_options={
                            "content-type": "image/jpeg" if self.selected_story_type == 'image' else "video/mp4"}
                    )

                media_url = vibe_db.storage.from_(bucket).get_public_url(file_name)

                my_id = vibe_db.auth.get_user().user.id
                caption = self.story_caption.text if hasattr(self, 'story_caption') else ""

                vibe_db.table("stories").insert({
                    "user_id": my_id,
                    "media_url": media_url,
                    "media_type": self.selected_story_type,
                    "caption": caption
                }).execute()

                show_snackbar("Hikaye paylaşıldı!")
                self.load_stories_preview()

            except Exception as e:
                show_snackbar(f"Hikaye yükleme hatası: {str(e)[:50]}", False)
            finally:
                self.ids.loading_spinner.active = False
        else:
            show_snackbar("Lütfen bir medya seçin", False)

    def view_story(self, story):
        self.manager.get_screen("story_view").stories = [story]
        self.manager.get_screen("story_view").current_story_index = 0
        self.manager.current = "story_view"

    def view_all_stories(self):
        self.manager.current = "story_view"

    def go_to_voice_match(self):
        self.manager.current = "voice_match"

    def send_post(self):
        post_text = self.ids.post_input.text.strip()
        if not post_text:
            show_snackbar("Lütfen bir şeyler yazın", False)
            return

        if len(post_text) > 500:
            show_snackbar("Gönderi 500 karakterden uzun olamaz", False)
            return

        try:
            user = vibe_db.auth.get_user().user
            u_name = MDApp.get_running_app().user_data.get("username", "Anonim")
            vibe_db.table("posts").insert({
                "user_id": user.id,
                "username": u_name,
                "content": post_text
            }).execute()
            self.ids.post_input.text = ""
            self.load_posts()
            show_snackbar("Gönderi paylaşıldı!")
        except Exception as e:
            show_snackbar(f"Hata: {str(e)[:50]}", False)

    def get_remaining_time(self, created_at_str):
        try:
            created_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            rem = (created_dt + timedelta(hours=24)) - datetime.now(timezone.utc)
            if rem.total_seconds() <= 0:
                return "⏰ Süre Doldu"
            h, r = divmod(int(rem.total_seconds()), 3600)
            m, _ = divmod(r, 60)
            return f"⏳ {h}s {m}d"
        except:
            return ""

    def load_posts(self):
        try:
            limit = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            posts = vibe_db.table("posts").select("*").gte("created_at", limit).order(
                "created_at", desc=True).limit(50).execute().data

            self.ids.feed_list.clear_widgets()
            my_id = vibe_db.auth.get_user().user.id

            for post in posts:
                # Beğeni sayısı
                likes_c = vibe_db.table("likes").select("id", count="exact").eq(
                    "post_id", post['id']).execute().count

                # Kendim beğendim mi?
                is_liked = vibe_db.table("likes").select("id").eq("post_id", post['id']).eq(
                    "user_id", my_id).execute().data

                # Yorum sayısı
                comm_c = vibe_db.table("comments").select("id", count="exact").eq(
                    "post_id", post['id']).execute().count

                # Post kartını oluştur
                card = MDCard(
                    orientation='vertical',
                    padding="12dp",
                    size_hint_y=None,
                    height="200dp",
                    radius=[15],
                    elevation=2,
                    md_bg_color=(0.95, 0.95, 0.95, 1) if MDApp.get_running_app().theme_cls.theme_style == "Light" else (
                        0.1, 0.1, 0.1, 1)
                )

                # Header
                header = MDBoxLayout(size_hint_y=None, height="35dp")
                user_btn = MDFlatButton(
                    text=f"@{post['username']}",
                    font_style="Subtitle2",
                    theme_text_color="Primary"
                )
                user_btn.bind(on_release=lambda x, uid=post['user_id']: self.view_profile(uid))
                header.add_widget(user_btn)

                header.add_widget(MDLabel(
                    text=self.get_remaining_time(post['created_at']),
                    halign="right",
                    font_style="Caption",
                    theme_text_color="Hint"
                ))

                # Kendi postunu silme butonu
                if str(post['user_id']) == str(my_id):
                    del_btn = MDIconButton(
                        icon="delete-outline",
                        theme_text_color="Error",
                        size_hint=(None, None),
                        size=("30dp", "30dp")
                    )
                    del_btn.bind(on_release=lambda x, p_id=post['id']: self.delete_post(p_id))
                    header.add_widget(del_btn)

                card.add_widget(header)

                # İçerik
                content_label = MDLabel(
                    text=post.get('content', ''),
                    font_style="Body1",
                    size_hint_y=None,
                    height="80dp"
                )
                card.add_widget(content_label)

                # Aksiyonlar
                actions = MDBoxLayout(size_hint_y=None, height="40dp", spacing="10dp")

                # Beğeni butonu
                like_btn = MDIconButton(
                    icon="heart" if is_liked else "heart-outline",
                    theme_text_color="Custom",
                    text_color=(1, 0, 0, 1) if is_liked else (0.5, 0.5, 0.5, 1)
                )
                l_lbl = MDLabel(
                    text=str(likes_c),
                    font_style="Caption",
                    adaptive_width=True
                )
                like_btn.bind(on_release=lambda x, p=post['id'], b=like_btn, l=l_lbl: self.toggle_like(p, b, l))

                # Yorum butonu
                comment_btn = MDIconButton(icon="comment-text-outline")
                c_lbl = MDLabel(
                    text=str(comm_c),
                    font_style="Caption",
                    adaptive_width=True
                )
                comment_btn.bind(on_release=lambda x, p=post: self.open_comment_list(p))

                actions.add_widget(like_btn)
                actions.add_widget(l_lbl)
                actions.add_widget(comment_btn)
                actions.add_widget(c_lbl)

                card.add_widget(actions)
                self.ids.feed_list.add_widget(card)

        except Exception as e:
            print(f"Post yükleme hatası: {e}")

    def view_profile(self, uid):
        if str(uid) == str(vibe_db.auth.get_user().user.id):
            self.manager.current = "profile"
        else:
            self.manager.get_screen("other_profile").target_user_id = uid
            self.manager.current = "other_profile"

    def delete_post(self, p_id):
        try:
            vibe_db.table("posts").delete().eq("id", p_id).execute()
            self.load_posts()
            show_snackbar("Gönderi silindi")
        except Exception as e:
            show_snackbar(f"Silme hatası: {str(e)[:50]}", False)

    def toggle_like(self, p_id, btn, lbl):
        uid = vibe_db.auth.get_user().user.id
        try:
            if btn.icon == "heart-outline":
                vibe_db.table("likes").insert({"post_id": p_id, "user_id": uid}).execute()
                btn.icon = "heart"
                btn.text_color = (1, 0, 0, 1)
                lbl.text = str(int(lbl.text) + 1)

                # Bildirim oluştur (post sahibine)
                post = vibe_db.table("posts").select("user_id").eq("id", p_id).single().execute()
                if post.data and str(post.data['user_id']) != str(uid):
                    vibe_db.table("notifications").insert({
                        "user_id": post.data['user_id'],
                        "from_user_id": uid,
                        "type": "like",
                        "post_id": p_id,
                        "read": False
                    }).execute()

            else:
                vibe_db.table("likes").delete().eq("post_id", p_id).eq("user_id", uid).execute()
                btn.icon = "heart-outline"
                btn.text_color = (0.5, 0.5, 0.5, 1)
                lbl.text = str(int(lbl.text) - 1)
        except Exception as e:
            show_snackbar(f"Beğeni hatası: {str(e)[:50]}", False)

    def open_comment_list(self, post):
        try:
            res = vibe_db.table("comments").select("*").eq("post_id", post['id']).order("created_at").execute()

            content = MDBoxLayout(
                orientation="vertical",
                spacing="10dp",
                size_hint_y=None,
                padding="10dp"
            )
            content.bind(minimum_height=content.setter('height'))

            # Yorum input alanı
            input_area = MDBoxLayout(size_hint_y=None, height="60dp", spacing="5dp")
            self.new_comment_input = MDTextField(
                hint_text="Yorumunu ekle...",
                mode="fill",
                multiline=True
            )
            send_btn = MDIconButton(
                icon="send",
                on_release=lambda x: self.post_comment(post['id'])
            )
            input_area.add_widget(self.new_comment_input)
            input_area.add_widget(send_btn)
            content.add_widget(input_area)

            # Yorumlar
            for c in res.data:
                comment_box = MDBoxLayout(
                    orientation="vertical",
                    spacing="2dp",
                    size_hint_y=None,
                    height="50dp"
                )
                username_label = MDLabel(
                    text=f"@{c['username']}",
                    font_style="Caption",
                    theme_text_color="Primary",
                    size_hint_y=None,
                    height="20dp"
                )
                comment_label = MDLabel(
                    text=c['content'],
                    font_style="Body2",
                    size_hint_y=None,
                    height="30dp"
                )
                comment_box.add_widget(username_label)
                comment_box.add_widget(comment_label)
                content.add_widget(comment_box)

            self.comment_dialog = MDDialog(
                title="💬 Yorumlar",
                type="custom",
                content_cls=content,
                size_hint=(0.9, 0.8)
            )
            self.comment_dialog.open()

        except Exception as e:
            show_snackbar(f"Yorum yükleme hatası: {str(e)[:50]}", False)

    def post_comment(self, p_id):
        txt = self.new_comment_input.text.strip()
        if not txt:
            show_snackbar("Lütfen yorum yazın", False)
            return

        if len(txt) > 200:
            show_snackbar("Yorum 200 karakterden uzun olamaz", False)
            return

        try:
            my_id = vibe_db.auth.get_user().user.id
            username = MDApp.get_running_app().user_data["username"]

            vibe_db.table("comments").insert({
                "post_id": p_id,
                "user_id": my_id,
                "username": username,
                "content": txt
            }).execute()

            # Bildirim oluştur
            post = vibe_db.table("posts").select("user_id").eq("id", p_id).single().execute()
            if post.data and str(post.data['user_id']) != str(my_id):
                vibe_db.table("notifications").insert({
                    "user_id": post.data['user_id'],
                    "from_user_id": my_id,
                    "type": "comment",
                    "post_id": p_id,
                    "read": False
                }).execute()

            self.comment_dialog.dismiss()
            self.load_posts()
            show_snackbar("Yorum eklendi!")

        except Exception as e:
            show_snackbar(f"Yorum ekleme hatası: {str(e)[:50]}", False)


class StoryViewScreen(Screen):
    current_story_index = 0
    stories = []

    def on_enter(self):
        self.load_stories()
        if self.stories:
            self.play_current_story()
        else:
            self.manager.current = "main"

    def load_stories(self):
        try:
            my_id = vibe_db.auth.get_user().user.id
            follows = vibe_db.table("follows").select("followed_id").eq("follower_id", my_id).execute()
            followed_ids = [f["followed_id"] for f in follows.data]
            followed_ids.append(my_id)

            time_limit = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            self.stories = vibe_db.table("stories").select("*, profiles(username)").in_("user_id", followed_ids).gte(
                "created_at", time_limit).order("created_at", desc=True).execute().data
            self.current_story_index = 0
        except Exception as e:
            show_snackbar(f"Hikaye yükleme hatası: {str(e)[:50]}", False)

    def play_current_story(self):
        if not self.stories:
            self.manager.current = "main"
            return

        story = self.stories[self.current_story_index]
        self.ids.story_username.text = f"@{story['profiles']['username']}"

        container = self.ids.story_container
        container.clear_widgets()

        if story['media_type'] == 'image':
            img = AsyncImage(
                source=story['media_url'],
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(1, 1)
            )
            container.add_widget(img)
        elif story['media_type'] == 'video':
            video = Video(
                source=story['media_url'],
                state='play',
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(1, 1)
            )
            container.add_widget(video)

        Clock.schedule_once(lambda dt: self.next_story(), 10)

    def next_story(self):
        if self.current_story_index < len(self.stories) - 1:
            self.current_story_index += 1
            self.play_current_story()
        else:
            self.manager.current = "main"

    def previous_story(self):
        if self.current_story_index > 0:
            self.current_story_index -= 1
            self.play_current_story()


class VoiceMatchScreen(Screen):
    match_dialog = None
    search_active = False

    def on_enter(self):
        self.search_active = False
        self.ids.status_label.text = "Eşleşme bekleniyor..."
        self.ids.search_btn.text = "EŞLEŞME ARA"
        self.ids.search_btn.md_bg_color = MDApp.get_running_app().theme_cls.primary_color

    def toggle_search(self):
        if not self.search_active:
            self.start_match_search()
        else:
            self.stop_match_search()

    def start_match_search(self):
        self.search_active = True
        self.ids.status_label.text = "Eşleşme aranıyor..."
        self.ids.search_btn.text = "ARAMAYI DURDUR"
        self.ids.search_btn.md_bg_color = (0.8, 0, 0, 1)

        # Thread ile arama yap
        threading.Thread(target=self.find_match, daemon=True).start()

    def find_match(self):
        my_id = vibe_db.auth.get_user().user.id

        try:
            rooms = vibe_db.table("voice_match_rooms").select("*").eq("status", "waiting").neq("user1_id",
                                                                                               my_id).execute()

            if rooms.data:
                room = rooms.data[0]
                vibe_db.table("voice_match_rooms").update({
                    "user2_id": my_id,
                    "status": "matched"
                }).eq("id", room['id']).execute()

                Clock.schedule_once(lambda dt: self.show_match_found(room['id'], room['user1_id']))
            else:
                new_room = vibe_db.table("voice_match_rooms").insert({
                    "user1_id": my_id,
                    "status": "waiting"
                }).execute()

                Clock.schedule_once(lambda dt: self.check_if_matched(new_room.data[0]['id']), 30)

        except Exception as e:
            print(f"Eşleşme hatası: {e}")

    def check_if_matched(self, room_id):
        if not self.search_active:
            return

        room = vibe_db.table("voice_match_rooms").select("*").eq("id", room_id).single().execute()

        if room.data['status'] == 'matched':
            Clock.schedule_once(lambda dt: self.show_match_found(room_id, room.data['user1_id']))
        else:
            vibe_db.table("voice_match_rooms").delete().eq("id", room_id).execute()
            Clock.schedule_once(lambda dt: self.show_no_match())

    def show_match_found(self, room_id, matched_user_id):
        if not self.search_active:
            return

        try:
            user = vibe_db.table("profiles").select("username").eq("id", matched_user_id).single().execute()
            username = user.data['username'] if user.data else "Anonim"

            content = MDBoxLayout(orientation="vertical", spacing="20dp", size_hint_y=None, height="200dp")
            content.add_widget(MDLabel(
                text=f"@{username} ile eşleştin!",
                halign="center",
                font_style="H6"
            ))

            self.match_dialog = MDDialog(
                title="🎉 Eşleşme Bulundu!",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(
                        text="Reddet",
                        on_release=lambda x: self.reject_match(room_id)
                    ),
                    MDRaisedButton(
                        text="Kabul Et",
                        on_release=lambda x: self.accept_match(room_id)
                    )
                ]
            )
            self.match_dialog.open()

        except Exception as e:
            show_snackbar(f"Eşleşme gösterim hatası: {str(e)[:50]}", False)

    def show_no_match(self):
        if self.search_active:
            self.ids.status_label.text = "Eşleşme bulunamadı. Tekrar deneyin."
            self.stop_match_search()

    def accept_match(self, room_id):
        self.match_dialog.dismiss()
        self.manager.get_screen("voice_chat_room").room_id = room_id
        self.manager.current = "voice_chat_room"
        self.stop_match_search()

    def reject_match(self, room_id):
        self.match_dialog.dismiss()
        vibe_db.table("voice_match_rooms").update({"status": "ended"}).eq("id", room_id).execute()
        self.stop_match_search()

    def stop_match_search(self):
        self.search_active = False
        self.ids.status_label.text = "Hazır"
        self.ids.search_btn.text = "EŞLEŞME ARA"
        self.ids.search_btn.md_bg_color = MDApp.get_running_app().theme_cls.primary_color


class VoiceChatRoomScreen(Screen):
    room_id = None
    media_menu = None

    def on_enter(self):
        if self.room_id:
            self.load_room_info()
            self.load_messages()
            Clock.schedule_interval(self.check_new_messages, 2)

    def on_leave(self):
        Clock.unschedule(self.check_new_messages)

    def check_new_messages(self, dt):
        self.load_messages()

    def load_room_info(self):
        try:
            room = vibe_db.table("voice_match_rooms").select("*, profiles!user1_id(username)").eq("id",
                                                                                                  self.room_id).single().execute()
            user1 = room.data['profiles']['username']
            user2_id = room.data['user2_id']

            if user2_id:
                user2 = vibe_db.table("profiles").select("username").eq("id", user2_id).single().execute()
                user2_name = user2.data['username']
                self.ids.room_title.title = f"{user1} & {user2_name}"
            else:
                self.ids.room_title.title = f"{user1}"
        except Exception as e:
            print(f"Oda bilgisi yükleme hatası: {e}")

    def load_messages(self):
        try:
            messages = vibe_db.table("room_messages").select("*, profiles(username)").eq("room_id", self.room_id).order(
                "created_at").execute()
            self.ids.room_chat_list.clear_widgets()

            my_id = vibe_db.auth.get_user().user.id

            for msg in messages.data:
                self.add_message_to_chat(msg, str(msg['user_id']) == str(my_id))
        except Exception as e:
            print(f"Mesaj yükleme hatası: {e}")

    def add_message_to_chat(self, msg, is_me):
        content_box = MDBoxLayout(orientation="vertical", spacing="5dp", size_hint_y=None, adaptive_height=True)

        if msg['message_type'] == 'text':
            content_box.add_widget(MDLabel(
                text=msg['content'],
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1) if is_me else (0, 0, 0, 1),
                size_hint_y=None,
                adaptive_height=True
            ))

        elif msg['message_type'] == 'image':
            img_box = MDBoxLayout(size_hint=(None, None), size=("200dp", "200dp"))
            img = AsyncImage(
                source=msg['media_url'],
                size_hint=(1, 1),
                keep_ratio=True,
                allow_stretch=True
            )
            img_box.add_widget(img)
            content_box.add_widget(img_box)

            if msg['content']:
                content_box.add_widget(MDLabel(
                    text=msg['content'],
                    size_hint_y=None,
                    height="20dp",
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1) if is_me else (0, 0, 0, 1)
                ))

        elif msg['message_type'] == 'video':
            video_box = MDBoxLayout(size_hint=(None, None), size=("200dp", "150dp"))
            video = Video(
                source=msg['media_url'],
                size_hint=(1, 1),
                state='stop'
            )
            video_box.add_widget(video)
            content_box.add_widget(video_box)

            if msg['content']:
                content_box.add_widget(MDLabel(
                    text=msg['content'],
                    size_hint_y=None,
                    height="20dp",
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1) if is_me else (0, 0, 0, 1)
                ))

        username_label = MDLabel(
            text=f"@{msg['profiles']['username']}",
            size_hint_y=None,
            height="20dp",
            font_style="Caption",
            theme_text_color="Hint"
        )

        main_box = MDBoxLayout(orientation="vertical", spacing="2dp", size_hint_y=None, adaptive_height=True)
        if not is_me:
            main_box.add_widget(username_label)
        main_box.add_widget(content_box)

        card = MDCard(
            main_box,
            size_hint=(0.7, None),
            adaptive_height=True,
            radius=[15, 15, 0, 15] if is_me else [15, 15, 15, 0],
            md_bg_color=MDApp.get_running_app().theme_cls.primary_color if is_me else (0.9, 0.9, 0.9, 1),
            pos_hint={"right": 1} if is_me else {"left": 1},
            padding="10dp",
            spacing="5dp"
        )

        self.ids.room_chat_list.add_widget(card)

    def open_media_menu(self):
        menu_items = [
            {
                "text": "📷 Fotoğraf Çek",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.take_photo(),
            },
            {
                "text": "🖼️ Galeriden Seç",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_from_gallery(),
            },
            {
                "text": "🎥 Video Çek",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.take_video(),
            },
        ]

        self.media_menu = MDDropdownMenu(
            caller=self.ids.media_btn,
            items=menu_items,
            width_mult=4,
        )
        self.media_menu.open()

    def take_photo(self):
        show_snackbar("Fotoğraf çekme özelliği aktif edilecek")

    def select_from_gallery(self):
        app = MDApp.get_running_app()
        app.file_manager = MDFileManager(
            exit_manager=app.exit_manager,
            select_path=self.select_media_path,
            preview=True
        )
        app.file_manager.show('/')

    def take_video(self):
        show_snackbar("Video çekme özelliği aktif edilecek")

    def select_media_path(self, path):
        if path:
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                self.send_media_message(path, 'image')
            elif path.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
                self.send_media_message(path, 'video')
            else:
                show_snackbar("Desteklenmeyen dosya formatı", False)

    def send_message(self):
        msg = self.ids.room_msg_input.text.strip()
        if msg:
            self.send_text_message(msg)
            self.ids.room_msg_input.text = ""

    def send_text_message(self, text):
        try:
            my_id = vibe_db.auth.get_user().user.id
            vibe_db.table("room_messages").insert({
                "room_id": self.room_id,
                "user_id": my_id,
                "message_type": "text",
                "content": text
            }).execute()
            self.load_messages()
        except Exception as e:
            show_snackbar(f"Mesaj gönderme hatası: {str(e)[:50]}", False)

    def send_media_message(self, file_path, media_type):
        try:
            # Dosya yükleme
            file_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
            bucket = "message_media"

            with open(file_path, 'rb') as f:
                vibe_db.storage.from_(bucket).upload(
                    file=file_path,
                    path=file_name,
                    file_options={"content-type": "image/jpeg" if media_type == 'image' else "video/mp4"}
                )

            media_url = vibe_db.storage.from_(bucket).get_public_url(file_name)

            my_id = vibe_db.auth.get_user().user.id
            vibe_db.table("room_messages").insert({
                "room_id": self.room_id,
                "user_id": my_id,
                "message_type": media_type,
                "content": "",
                "media_url": media_url
            }).execute()

            self.load_messages()
            show_snackbar("Medya gönderildi!")
        except Exception as e:
            show_snackbar(f"Medya gönderme hatası: {str(e)[:50]}", False)

    def end_chat(self):
        try:
            vibe_db.table("voice_match_rooms").update({
                "status": "ended",
                "ended_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", self.room_id).execute()
        except:
            pass
        self.manager.current = "main"


class ChatScreen(Screen):
    room_id, target_name = None, ""
    file_manager = None
    media_menu = None

    def on_enter(self):
        self.ids.chat_title.title = f"@{self.target_name}"
        self.load()
        Clock.schedule_interval(self.check_new_messages, 2)

    def on_leave(self):
        Clock.unschedule(self.check_new_messages)

    def check_new_messages(self, dt):
        self.load()

    def load(self):
        try:
            res = vibe_db.table("messages").select("*").eq("room_id", self.room_id).order("created_at").execute().data
            self.ids.chat_list.clear_widgets()
            my_id = vibe_db.auth.get_user().user.id

            for m in res:
                is_me = str(m['sender_id']) == str(my_id)
                content_box = MDBoxLayout(orientation="vertical", spacing="5dp", size_hint_y=None, adaptive_height=True)

                if m.get('message_type', 'text') == 'text':
                    content_box.add_widget(MDLabel(
                        text=m['text'],
                        theme_text_color="Custom",
                        text_color=(1, 1, 1, 1) if is_me else (0, 0, 0, 1),
                        size_hint_y=None,
                        adaptive_height=True
                    ))
                elif m.get('message_type') == 'image':
                    img_box = MDBoxLayout(size_hint=(None, None), size=("200dp", "200dp"))
                    img = AsyncImage(
                        source=m.get('media_url', ''),
                        size_hint=(1, 1),
                        keep_ratio=True,
                        allow_stretch=True
                    )
                    img_box.add_widget(img)
                    content_box.add_widget(img_box)
                elif m.get('message_type') == 'video':
                    video_box = MDBoxLayout(size_hint=(None, None), size=("200dp", "150dp"))
                    video = Video(
                        source=m.get('media_url', ''),
                        size_hint=(1, 1),
                        state='stop'
                    )
                    video_box.add_widget(video)
                    content_box.add_widget(video_box)

                card = MDCard(
                    content_box,
                    padding="10dp",
                    size_hint=(0.7, None),
                    adaptive_height=True,
                    radius=[15, 15, 0, 15] if is_me else [15, 15, 15, 0],
                    md_bg_color=MDApp.get_running_app().theme_cls.primary_color if is_me else (0.9, 0.9, 0.9, 1),
                    pos_hint={"right": 1} if is_me else {"left": 1}
                )
                self.ids.chat_list.add_widget(card)
        except Exception as e:
            show_snackbar(f"Mesaj yükleme hatası: {str(e)[:50]}", False)

    def open_media_menu(self):
        menu_items = [
            {
                "text": "📷 Fotoğraf Çek",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.take_photo(),
            },
            {
                "text": "🖼️ Galeriden Seç",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_from_gallery(),
            },
            {
                "text": "🎥 Video Çek",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.take_video(),
            },
        ]

        self.media_menu = MDDropdownMenu(
            caller=self.ids.media_btn,
            items=menu_items,
            width_mult=4,
        )
        self.media_menu.open()

    def take_photo(self):
        show_snackbar("Fotoğraf çekme özelliği aktif edilecek")

    def select_from_gallery(self):
        app = MDApp.get_running_app()
        app.current_chat_screen = self
        app.file_manager = MDFileManager(
            exit_manager=app.exit_manager,
            select_path=self.select_media_path,
            preview=True
        )
        app.file_manager.show('/')

    def take_video(self):
        show_snackbar("Video çekme özelliği aktif edilecek")

    def select_media_path(self, path):
        if path:
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                self.send_media_message(path, 'image')
            elif path.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
                self.send_media_message(path, 'video')
            else:
                show_snackbar("Desteklenmeyen dosya formatı", False)
        if self.file_manager:
            self.file_manager.close()

    def send_message(self):
        msg = self.ids.msg_input.text.strip()
        if not msg:
            show_snackbar("Lütfen mesaj yazın", False)
            return

        try:
            my_id = vibe_db.auth.get_user().user.id
            vibe_db.table("messages").insert({
                "room_id": self.room_id,
                "sender_id": my_id,
                "message_type": "text",
                "text": msg
            }).execute()
            self.ids.msg_input.text = ""
            self.load()
        except Exception as e:
            show_snackbar(f"Mesaj gönderme hatası: {str(e)[:50]}", False)

    def send_media_message(self, file_path, media_type):
        try:
            file_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
            bucket = "message_media"

            with open(file_path, 'rb') as f:
                vibe_db.storage.from_(bucket).upload(
                    file=file_path,
                    path=file_name,
                    file_options={"content-type": "image/jpeg" if media_type == 'image' else "video/mp4"}
                )

            media_url = vibe_db.storage.from_(bucket).get_public_url(file_name)

            my_id = vibe_db.auth.get_user().user.id
            vibe_db.table("messages").insert({
                "room_id": self.room_id,
                "sender_id": my_id,
                "message_type": media_type,
                "media_url": media_url,
                "text": ""
            }).execute()

            self.load()
            show_snackbar("Medya gönderildi!")
        except Exception as e:
            show_snackbar(f"Medya gönderme hatası: {str(e)[:50]}", False)


class ProfileScreen(Screen):
    edit_dialog = None
    logout_dialog = None
    profile_photo_path = None

    def on_enter(self):
        self.load_profile_data()

    def calculate_age(self, birth_date_str):
        if not birth_date_str:
            return "--"
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return str(age)
        except:
            return "--"

    def load_profile_data(self):
        try:
            user = vibe_db.auth.get_user().user
            p = vibe_db.table("profiles").select("*").eq("id", user.id).single().execute().data

            self.ids.profile_name.text = f"@{p.get('username', 'isimsiz')}"
            self.ids.user_bio.text = p.get('bio') if p.get('bio') else "Henüz bir biyografi eklenmedi."
            self.ids.user_location.text = f"{p.get('city', 'Şehir')}, {p.get('country', 'Ülke')}"
            self.ids.user_age.text = f"{self.calculate_age(p.get('birth_date'))} Yaşında"

            # Profil fotoğrafı varsa göster
            if p.get('profile_photo'):
                self.ids.profile_avatar.source = p['profile_photo']
                self.ids.profile_avatar.icon = ""
            else:
                self.ids.profile_avatar.source = ""
                self.ids.profile_avatar.icon = "account-circle"

            # İstatistikler
            posts_res = vibe_db.table("posts").select("id", count="exact").eq("user_id", user.id).execute()
            self.ids.post_count.text = str(posts_res.count)

            followers = vibe_db.table("follows").select("id", count="exact").eq("followed_id", user.id).execute()
            self.ids.follower_count.text = str(followers.count)

            following = vibe_db.table("follows").select("id", count="exact").eq("follower_id", user.id).execute()
            self.ids.following_count.text = str(following.count)

            self.load_my_vibes(user.id)

        except Exception as e:
            show_snackbar(f"Profil hatası: {str(e)[:50]}", False)

    def load_my_vibes(self, user_id):
        self.ids.my_vibe_grid.clear_widgets()
        try:
            res = vibe_db.table("posts").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(
                9).execute()
            for post in res.data:
                card = MDCard(
                    size_hint=(None, None),
                    size=("105dp", "105dp"),
                    md_bg_color=(0.1, 0.1, 0.1, 1),
                    radius=[10],
                    on_release=lambda x, p=post: self.view_post_detail(p)
                )
                card.add_widget(MDLabel(
                    text=post['content'][:20] + ("..." if len(post['content']) > 20 else ""),
                    halign="center",
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1),
                    font_style="Caption"
                ))
                self.ids.my_vibe_grid.add_widget(card)
        except Exception as e:
            print(f"Vibe yükleme hatası: {e}")

    def view_post_detail(self, post):
        # Post detayını göster (basit bir dialog)
        content = MDBoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None)
        content.add_widget(MDLabel(
            text=f"@{post['username']}",
            font_style="H6",
            theme_text_color="Primary"
        ))
        content.add_widget(MDLabel(
            text=post['content'],
            font_style="Body1"
        ))

        dialog = MDDialog(
            title="Gönderi Detayı",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Kapat",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def open_edit_dialog(self):
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="350dp")

        self.edit_name = MDTextField(
            hint_text="Kullanıcı Adı",
            text=self.ids.profile_name.text.replace("@", "")
        )
        self.edit_bio = MDTextField(
            hint_text="Biyografi",
            text=self.ids.user_bio.text,
            multiline=True
        )
        self.edit_city = MDTextField(
            hint_text="Şehir",
            text=self.ids.user_location.text.split(",")[0]
        )
        self.edit_country = MDTextField(
            hint_text="Ülke",
            text=self.ids.user_location.text.split(",")[-1].strip()
        )

        for w in [self.edit_name, self.edit_bio, self.edit_city, self.edit_country]:
            content.add_widget(w)

        # Profil fotoğrafı yükleme butonu
        photo_btn = MDRaisedButton(
            text="📷 Profil Fotoğrafı Yükle",
            size_hint=(1, None),
            height="40dp",
            on_release=lambda x: self.select_profile_photo()
        )
        content.add_widget(photo_btn)

        self.edit_dialog = MDDialog(
            title="Profili Düzenle",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="İPTAL",
                    on_release=lambda x: self.edit_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="KAYDET",
                    on_release=lambda x: self.save_profile()
                )
            ]
        )
        self.edit_dialog.open()

    def select_profile_photo(self):
        app = MDApp.get_running_app()
        app.current_screen = self
        app.file_manager = MDFileManager(
            exit_manager=app.exit_manager,
            select_path=self.set_profile_photo,
            preview=True
        )
        app.file_manager.show('/')

    def set_profile_photo(self, path):
        if path and path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            self.profile_photo_path = path
            show_snackbar("Profil fotoğrafı seçildi")

    def save_profile(self):
        try:
            user = vibe_db.auth.get_user().user
            update_data = {
                "username": self.edit_name.text.strip(),
                "bio": self.edit_bio.text.strip(),
                "city": self.edit_city.text.strip(),
                "country": self.edit_country.text.strip()
            }

            # Profil fotoğrafı yükle
            if self.profile_photo_path:
                file_name = f"{uuid.uuid4()}_{os.path.basename(self.profile_photo_path)}"
                bucket = "profile_photos"

                with open(self.profile_photo_path, 'rb') as f:
                    vibe_db.storage.from_(bucket).upload(
                        file=self.profile_photo_path,
                        path=file_name,
                        file_options={"content-type": "image/jpeg"}
                    )

                media_url = vibe_db.storage.from_(bucket).get_public_url(file_name)
                update_data["profile_photo"] = media_url

            vibe_db.table("profiles").update(update_data).eq("id", user.id).execute()

            self.edit_dialog.dismiss()
            self.load_profile_data()
            show_snackbar("Profil güncellendi!")

        except Exception as e:
            show_snackbar(f"Profil güncelleme hatası: {str(e)[:50]}", False)

    def toggle_theme(self):
        """Dark/Light mode değiştir"""
        app = MDApp.get_running_app()
        user = vibe_db.auth.get_user().user

        if app.theme_cls.theme_style == "Light":
            app.theme_cls.theme_style = "Dark"
            dark_mode = True
        else:
            app.theme_cls.theme_style = "Light"
            dark_mode = False

        # Tercihi kaydet
        try:
            vibe_db.table("user_preferences").upsert({
                "user_id": user.id,
                "dark_mode": dark_mode
            }).execute()
        except:
            pass

        show_snackbar(f"Tema değiştirildi: {'Koyu' if dark_mode else 'Açık'}")

    def logout(self):
        """Çıkış yap - önce onayla"""
        self.logout_dialog = MDDialog(
            title="Çıkış Yap",
            text="Hesabınızdan çıkış yapmak istediğinize emin misiniz?",
            buttons=[
                MDFlatButton(
                    text="İptal",
                    on_release=lambda x: self.logout_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Çıkış Yap",
                    on_release=lambda x: self.perform_logout()
                )
            ]
        )
        self.logout_dialog.open()

    def perform_logout(self):
        """Gerçek çıkış işlemi"""
        try:
            vibe_db.auth.sign_out()
            self.logout_dialog.dismiss()
            show_snackbar("Başarıyla çıkış yapıldı")
            self.manager.current = "login"
        except Exception as e:
            show_snackbar(f"Çıkış hatası: {str(e)[:50]}", False)


class OtherProfileScreen(Screen):
    target_user_id = None

    def on_enter(self):
        if self.target_user_id:
            self.load_target_profile()
            self.check_follow_status()

    def load_target_profile(self):
        try:
            p_res = vibe_db.table("profiles").select("*").eq("id", self.target_user_id).single().execute()
            p = p_res.data
            self.ids.target_name.text = f"@{p.get('username', 'isimsiz')}"
            self.ids.target_bio.text = p.get('bio') if p.get('bio') else "Biyografi yok."
            self.ids.target_location.text = f"{p.get('city', 'Şehir')}, {p.get('country', 'Ülke')}"

            # Profil fotoğrafı
            if p.get('profile_photo'):
                self.ids.target_avatar.source = p['profile_photo']
                self.ids.target_avatar.icon = ""
            else:
                self.ids.target_avatar.source = ""
                self.ids.target_avatar.icon = "account-circle"

            # İstatistikler
            posts_count = vibe_db.table("posts").select("id", count="exact").eq("user_id",
                                                                                self.target_user_id).execute().count
            followers_count = vibe_db.table("follows").select("id", count="exact").eq("followed_id",
                                                                                      self.target_user_id).execute().count

            self.ids.target_post_count.text = str(posts_count)
            self.ids.target_follower_count.text = str(followers_count)

            self.ids.target_vibe_grid.clear_widgets()
            res = vibe_db.table("posts").select("*").eq("user_id", self.target_user_id).order("created_at",
                                                                                              desc=True).limit(
                9).execute()
            for post in res.data:
                card = MDCard(
                    size_hint=(None, None),
                    size=("105dp", "105dp"),
                    md_bg_color=(0.1, 0.1, 0.1, 1),
                    radius=[10]
                )
                card.add_widget(MDLabel(
                    text=post['content'][:20] + "...",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1),
                    font_style="Caption"
                ))
                self.ids.target_vibe_grid.add_widget(card)
        except Exception as e:
            show_snackbar(f"Profil yükleme hatası: {str(e)[:50]}", False)

    def check_follow_status(self):
        my_id = vibe_db.auth.get_user().user.id
        res = vibe_db.table("follows").select("id").eq("follower_id", my_id).eq("followed_id",
                                                                                self.target_user_id).execute()
        if res.data:
            self.ids.follow_btn.text = "Takibi Bırak"
            self.ids.follow_btn.md_bg_color = (0.8, 0.8, 0.8, 1)
        else:
            self.ids.follow_btn.text = "Takip Et"
            self.ids.follow_btn.md_bg_color = MDApp.get_running_app().theme_cls.primary_color

    def toggle_follow(self):
        my_id = vibe_db.auth.get_user().user.id
        try:
            if self.ids.follow_btn.text == "Takip Et":
                vibe_db.table("follows").insert({
                    "follower_id": my_id,
                    "followed_id": self.target_user_id
                }).execute()
                show_snackbar("Takip ediliyor")
            else:
                vibe_db.table("follows").delete().eq("follower_id", my_id).eq("followed_id",
                                                                              self.target_user_id).execute()
                show_snackbar("Takipten çıkıldı")
            self.check_follow_status()
        except Exception as e:
            show_snackbar(f"Takip işlemi hatası: {str(e)[:50]}", False)

    def start_chat(self):
        my_id = vibe_db.auth.get_user().user.id
        try:
            res = vibe_db.table("chat_rooms").select("*").or_(
                f"and(user_one.eq.{my_id},user_two.eq.{self.target_user_id}),"
                f"and(user_one.eq.{self.target_user_id},user_two.eq.{my_id})"
            ).execute()

            if res.data:
                room_id = res.data[0]['id']
            else:
                new_room = vibe_db.table("chat_rooms").insert({
                    "user_one": my_id,
                    "user_two": self.target_user_id
                }).execute()
                room_id = new_room.data[0]['id']

            c = self.manager.get_screen("chat")
            c.room_id = room_id
            c.target_name = self.ids.target_name.text.replace("@", "")
            self.manager.current = "chat"

        except Exception as e:
            show_snackbar(f"Sohbet başlatma hatası: {str(e)[:50]}", False)


class SearchScreen(Screen):
    filter_dialog = None
    current_filters = {"city": "", "min_age": "", "max_age": ""}

    def search_user(self, text):
        if len(text) < 2:
            return

        self.ids.search_results.clear_widgets()
        try:
            query = vibe_db.table("profiles").select("id, username, city, birth_date")

            # İsim filtresi
            query = query.ilike("username", f"%{text}%")

            # Şehir filtresi
            if self.current_filters["city"]:
                query = query.ilike("city", f"%{self.current_filters['city']}%")

            res = query.execute()

            for user in res.data:
                if str(user['id']) == str(vibe_db.auth.get_user().user.id):
                    continue

                # Yaş filtresi
                age = self.calculate_age(user.get('birth_date'))
                if self.current_filters["min_age"]:
                    if age == "--" or int(age) < int(self.current_filters["min_age"]):
                        continue
                if self.current_filters["max_age"]:
                    if age == "--" or int(age) > int(self.current_filters["max_age"]):
                        continue

                item = TwoLineAvatarListItem(
                    text=f"@{user['username']}",
                    secondary_text=f"{user.get('city', 'Şehir belirtilmemiş')} • {age} yaş"
                )
                item.add_widget(IconLeftWidget(icon="account-search"))
                item.bind(on_release=lambda x, uid=user['id']: self.go_to_profile(uid))
                self.ids.search_results.add_widget(item)

        except Exception as e:
            show_snackbar(f"Arama hatası: {str(e)[:50]}", False)

    def calculate_age(self, birth_date_str):
        if not birth_date_str:
            return "--"
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return str(age)
        except:
            return "--"

    def go_to_profile(self, uid):
        self.manager.get_screen("other_profile").target_user_id = uid
        self.manager.current = "other_profile"

    def open_filter_dialog(self):
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="220dp")

        self.filter_city = MDTextField(
            hint_text="Şehir",
            text=self.current_filters["city"]
        )
        self.filter_min_age = MDTextField(
            hint_text="Minimum yaş",
            text=self.current_filters["min_age"],
            input_filter="int"
        )
        self.filter_max_age = MDTextField(
            hint_text="Maksimum yaş",
            text=self.current_filters["max_age"],
            input_filter="int"
        )

        content.add_widget(self.filter_city)
        content.add_widget(self.filter_min_age)
        content.add_widget(self.filter_max_age)

        self.filter_dialog = MDDialog(
            title="🔍 Filtrele",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Temizle",
                    on_release=lambda x: self.clear_filters()
                ),
                MDRaisedButton(
                    text="Uygula",
                    on_release=lambda x: self.apply_filters()
                )
            ]
        )
        self.filter_dialog.open()

    def apply_filters(self):
        self.current_filters = {
            "city": self.filter_city.text.strip(),
            "min_age": self.filter_min_age.text.strip(),
            "max_age": self.filter_max_age.text.strip()
        }

        # Geçerli arama metni varsa yeniden ara
        current_text = self.ids.search_field.text
        if current_text:
            self.search_user(current_text)

        self.filter_dialog.dismiss()
        show_snackbar("Filtreler uygulandı")

    def clear_filters(self):
        self.current_filters = {"city": "", "min_age": "", "max_age": ""}
        self.filter_city.text = ""
        self.filter_min_age.text = ""
        self.filter_max_age.text = ""

        # Geçerli arama metni varsa yeniden ara
        current_text = self.ids.search_field.text
        if current_text:
            self.search_user(current_text)

        show_snackbar("Filtreler temizlendi")


class MessageListScreen(Screen):
    def on_enter(self):
        try:
            my_id = vibe_db.auth.get_user().user.id
            res = vibe_db.table("chat_rooms").select("*").or_(f"user_one.eq.{my_id},user_two.eq.{my_id}").execute()
            self.ids.room_list.clear_widgets()
            for r in res.data:
                t_id = r['user_two'] if str(r['user_one']) == str(my_id) else r['user_one']
                p = vibe_db.table("profiles").select("username", "id").eq("id", t_id).single().execute().data
                item = TwoLineAvatarListItem(text=f"@{p['username']}", secondary_text="Mesajı gör")
                item.add_widget(IconLeftWidget(icon="account"))
                item.bind(on_release=lambda x, rid=r['id'], n=p['username']: self.go(rid, n))
                self.ids.room_list.add_widget(item)
        except Exception as e:
            show_snackbar(f"Mesaj listesi hatası: {str(e)[:50]}", False)

    def go(self, rid, n):
        c = self.manager.get_screen("chat")
        c.room_id = rid
        c.target_name = n
        self.manager.current = "chat"


class VibeApp(MDApp):
    user_data = {"username": "", "birthdate": "", "user_id": ""}
    file_manager = None
    current_chat_screen = None
    current_screen = None

    def build(self):
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV)

    def exit_manager(self, *args):
        if self.file_manager:
            self.file_manager.close()

    def select_media_for_chat(self, path):
        if self.current_chat_screen:
            self.current_chat_screen.select_media_path(path)


KV = '''
#:import MDChip kivymd.uix.chip.MDChip

ScreenManager:
    LoginScreen:
    SignupScreen:
    UsernameScreen:
    BirthDateScreen:
    LoadingScreen:
    MainScreen:
    SearchScreen:
    ProfileScreen:
    OtherProfileScreen:
    MessageListScreen:
    ChatScreen:
    StoryViewScreen:
    VoiceMatchScreen:
    VoiceChatRoomScreen:

<LoadingScreen>:
    name: "loading"
    MDBoxLayout:
        orientation: "vertical"
        padding: "50dp"
        spacing: "30dp"
        MDSpinner:
            size_hint: None, None
            size: dp(46), dp(46)
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            active: True
        MDLabel:
            text: "Yükleniyor..."
            halign: "center"
            font_style: "H6"
            theme_text_color: "Primary"

<LoginScreen>:
    name: "login"
    MDBoxLayout:
        orientation: "vertical"
        padding: "30dp"
        spacing: "15dp"

        MDIcon:
            icon: "account-circle"
            font_size: "60sp"
            halign: "center"
            theme_text_color: "Primary"

        MDLabel:
            text: "Vibe+ Giriş"
            font_style: "H5"
            halign: "center"
            size_hint_y: None
            height: "40dp"

        MDTextField:
            id: email
            hint_text: "E-posta"
            icon_left: "email"
            mode: "fill"
            size_hint_y: None
            height: "50dp"

        MDTextField:
            id: password
            hint_text: "Şifre"
            password: True
            icon_left: "lock"
            mode: "fill"
            size_hint_y: None
            height: "50dp"

        MDRaisedButton:
            text: "GİRİŞ YAP"
            size_hint_x: 1
            size_hint_y: None
            height: "45dp"
            md_bg_color: app.theme_cls.primary_color
            on_release: root.login_user()

        MDBoxLayout:
            size_hint_y: None
            height: "30dp"
            spacing: "5dp"

            MDFlatButton:
                text: "Şifremi Unuttum"
                size_hint_x: 0.5
                theme_text_color: "Secondary"
                font_size: "12sp"
                on_release: root.open_reset_dialog()

            MDFlatButton:
                text: "Hesap Oluştur"
                size_hint_x: 0.5
                theme_text_color: "Primary"
                font_size: "12sp"
                on_release: root.manager.current = "signup"

<SignupScreen>:
    name: "signup"
    MDBoxLayout:
        orientation: "vertical"
        padding: "30dp"
        spacing: "15dp"

        MDLabel:
            text: "Yeni Hesap"
            font_style: "H4"
            halign: "center"
            size_hint_y: None
            height: "40dp"

        MDTextField:
            id: new_email
            hint_text: "E-posta"
            icon_left: "email"
            mode: "fill"
            size_hint_y: None
            height: "50dp"

        MDTextField:
            id: new_password
            hint_text: "Şifre (min 6 karakter)"
            password: True
            icon_left: "lock"
            mode: "fill"
            size_hint_y: None
            height: "50dp"

        MDRaisedButton:
            text: "KAYIT OL"
            size_hint_x: 1
            size_hint_y: None
            height: "45dp"
            md_bg_color: app.theme_cls.primary_color
            on_release: root.signup_user()

        MDFlatButton:
            text: "Zaten hesabın var mı? Giriş Yap"
            pos_hint: {"center_x": .5}
            on_release: root.manager.current = "login"

<UsernameScreen>:
    name: "username"
    MDBoxLayout:
        orientation: "vertical"
        padding: "30dp"
        spacing: "20dp"

        MDLabel:
            text: "Sana ne diyelim?"
            font_style: "H5"
            halign: "center"
            size_hint_y: None
            height: "40dp"

        MDTextField:
            id: username_input
            hint_text: "Kullanıcı Adı (min 3 karakter)"
            icon_left: "account"
            mode: "fill"
            size_hint_y: None
            height: "50dp"

        MDRaisedButton:
            text: "DEVAM ET"
            size_hint_x: 1
            size_hint_y: None
            height: "45dp"
            on_release: root.save_username()

<BirthDateScreen>:
    name: "birthdate"
    MDBoxLayout:
        orientation: "vertical"
        padding: "30dp"
        spacing: "20dp"

        MDLabel:
            text: "Doğum Tarihin"
            font_style: "H5"
            halign: "center"
            size_hint_y: None
            height: "40dp"

        MDRaisedButton:
            text: "📅 Doğum Tarihini Seç"
            size_hint_x: 1
            size_hint_y: None
            height: "45dp"
            on_release: root.show_date_picker()

        MDLabel:
            id: selected_date_label
            text: "Tarih seçilmedi"
            halign: "center"
            font_style: "H6"
            theme_text_color: "Primary"

        MDRaisedButton:
            text: "KURULUMU TAMAMLA"
            size_hint_x: 1
            size_hint_y: None
            height: "45dp"
            md_bg_color: (0.2, 0.7, 0.3, 1)
            on_release: root.finish_onboarding()

<MainScreen>:
    name: "main"
    loading: False

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Vibe+"
            left_action_items: [["account-circle", lambda x: setattr(root.manager, 'current', 'profile')]]
            right_action_items: 
                [
                ["bell", lambda x: None],
                ["magnify", lambda x: setattr(root.manager, 'current', 'search')], 
                ["message", lambda x: setattr(root.manager, 'current', 'msg_list')]
                ]

            MDBoxLayout:
                size_hint: None, None
                size: "24dp", "24dp"
                pos_hint: {"center_x": .85, "center_y": .8}
                md_bg_color: (1, 0, 0, 1)
                radius: [12]

                MDLabel:
                    id: notification_badge
                    text: ""
                    halign: "center"
                    valign: "center"
                    font_size: "10sp"
                    theme_text_color: "Custom"
                    text_color: (1, 1, 1, 1)
                    opacity: 0

        MDBoxLayout:
            orientation: "vertical"
            padding: "15dp"
            spacing: "15dp"

            MDBoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: "70dp"
                padding: "10dp"
                spacing: "10dp"

                MDLabel:
                    text: "Hikayeler"
                    bold: True
                    size_hint_x: None
                    width: "100dp"

                MDBoxLayout:
                    id: stories_container
                    spacing: "5dp"

                MDFlatButton:
                    text: "Tümü"
                    size_hint_x: None
                    width: "50dp"
                    on_release: root.view_all_stories()

            MDBoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: "50dp"
                spacing: "10dp"

                MDRaisedButton:
                    text: "🎤 Sesli Eşleş"
                    size_hint_x: 0.5
                    on_release: root.go_to_voice_match()

                MDRaisedButton:
                    text: "📸 Hikaye Ekle"
                    size_hint_x: 0.5
                    on_release: root.open_story_creator()

            MDLabel:
                id: welcome_msg
                adaptive_height: True
                bold: True
                font_style: "H6"

            MDTextField:
                id: post_input
                hint_text: "Neler oluyor? (max 500 karakter)"
                mode: "fill"
                multiline: True
                max_text_length: 500

            MDRaisedButton:
                text: "Vibe'la"
                pos_hint: {"right": 1}
                size_hint_x: 0.3
                on_release: root.send_post()

            ScrollView:
                id: scroll_view
                on_scroll_stop: root.on_scroll_stop()

                MDBoxLayout:
                    id: feed_list
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "15dp"
                    padding: ["0dp", "10dp"]

            MDSpinner:
                id: refresh_spinner
                size_hint: None, None
                size: dp(36), dp(36)
                pos_hint: {'center_x': 0.5}
                active: False
                opacity: 0

        MDSpinner:
            id: loading_spinner
            size_hint: None, None
            size: dp(46), dp(46)
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            active: False
            opacity: 0

<StoryViewScreen>:
    name: "story_view"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0, 0, 0, 1

        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: "50dp"
            padding: "10dp"

            MDLabel:
                id: story_username
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                bold: True
                font_size: "18sp"

            Widget:
                size_hint_x: 0.7

            MDIconButton:
                icon: "close"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                on_release: root.manager.current = "main"

        BoxLayout:
            id: story_container

        MDBoxLayout:
            size_hint_y: None
            height: "50dp"

            MDRaisedButton:
                text: "← Önceki"
                size_hint_x: 0.5
                on_release: root.previous_story()

            MDRaisedButton:
                text: "Sonraki →"
                size_hint_x: 0.5
                on_release: root.next_story()

<VoiceMatchScreen>:
    name: "voice_match"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Sesli Eşleşme"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'main')]]

        MDBoxLayout:
            orientation: "vertical"
            padding: "40dp"
            spacing: "40dp"

            MDIcon:
                icon: "microphone"
                font_size: "80sp"
                halign: "center"
                theme_text_color: "Primary"

            MDLabel:
                id: status_label
                text: "Hazır"
                halign: "center"
                font_style: "H5"

            MDLabel:
                text: "Rastgele bir kişiyle sesli sohbet başlat"
                halign: "center"
                theme_text_color: "Secondary"

            MDRaisedButton:
                id: search_btn
                text: "EŞLEŞME ARA"
                size_hint_x: 1
                font_size: "18sp"
                on_release: root.toggle_search()

            MDLabel:
                text: "• Eşleşme bulunursa bildirim alacaksın\\n• Reddetmek için 30 saniyen var\\n• Konuşma bitince oda kapanır"
                halign: "center"
                theme_text_color: "Hint"
                font_size: "12sp"

<VoiceChatRoomScreen>:
    name: "voice_chat_room"
    room_id: None

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: room_title
            left_action_items: [["arrow-left", lambda x: root.end_chat()]]
            right_action_items: [["phone-hangup", lambda x: root.end_chat()]]

        ScrollView:
            MDBoxLayout:
                id: room_chat_list
                orientation: "vertical"
                adaptive_height: True
                padding: "15dp"
                spacing: "12dp"

        MDBoxLayout:
            size_hint_y: None
            height: "70dp"
            padding: "10dp"
            md_bg_color: app.theme_cls.bg_dark if app.theme_cls.theme_style == "Dark" else (1, 1, 1, 1)

            MDIconButton:
                id: media_btn
                icon: "attachment"
                on_release: root.open_media_menu()

            MDTextField:
                id: room_msg_input
                hint_text: "Mesaj yaz..."
                mode: "round"
                size_hint_x: 0.8

            MDIconButton:
                icon: "send"
                on_release: root.send_message()

<ChatScreen>:
    name: "chat"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: chat_title
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'msg_list')]]
            right_action_items: [["attachment", lambda x: root.open_media_menu()]]

        ScrollView:
            MDBoxLayout:
                id: chat_list
                orientation: "vertical"
                adaptive_height: True
                padding: "15dp"
                spacing: "12dp"

        MDBoxLayout:
            size_hint_y: None
            height: "70dp"
            padding: "10dp"
            md_bg_color: app.theme_cls.bg_dark if app.theme_cls.theme_style == "Dark" else (1, 1, 1, 1)

            MDTextField:
                id: msg_input
                hint_text: "Bir şeyler yaz..."
                mode: "round"
                size_hint_x: 0.8

            MDIconButton:
                icon: "send"
                on_release: root.send_message()

<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Vibe Ara"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'main')]]
            right_action_items: [["filter", lambda x: root.open_filter_dialog()]]

        MDBoxLayout:
            orientation: "vertical"
            padding: "10dp"

            MDTextField:
                id: search_field
                hint_text: "Kullanıcı adı yaz..."
                icon_left: "magnify"
                mode: "round"
                on_text: root.search_user(self.text)

            ScrollView:
                MDList:
                    id: search_results

<ProfileScreen>:
    name: "profile"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Profilim"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'main')]]
            right_action_items: [["theme-light-dark", lambda x: root.toggle_theme()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: "20dp"
                spacing: "15dp"

                MDIconButton:
                    id: profile_avatar
                    icon: "account-circle"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    pos_hint: {"center_x": .5}
                    font_size: "80sp"
                    size_hint: None, None
                    size: "100dp", "100dp"

                MDLabel:
                    id: profile_name
                    halign: "center"
                    font_style: "H5"
                    bold: True

                MDLabel:
                    id: user_bio
                    halign: "center"
                    theme_text_color: "Secondary"
                    font_style: "Body1"

                MDBoxLayout:
                    adaptive_height: True
                    spacing: "20dp"
                    pos_hint: {"center_x": .5}

                    MDLabel:
                        id: user_location
                        adaptive_width: True
                        font_style: "Caption"

                    MDLabel:
                        id: user_age
                        adaptive_width: True
                        font_style: "Caption"

                MDBoxLayout:
                    padding: "10dp"
                    spacing: "20dp"

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: "5dp"

                        MDLabel:
                            text: "Vibe"
                            halign: "center"
                            font_style: "Caption"

                        MDLabel:
                            id: post_count
                            halign: "center"
                            font_style: "H6"
                            bold: True

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: "5dp"

                        MDLabel:
                            text: "Takipçi"
                            halign: "center"
                            font_style: "Caption"

                        MDLabel:
                            id: follower_count
                            halign: "center"
                            font_style: "H6"
                            bold: True

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: "5dp"

                        MDLabel:
                            text: "Takip"
                            halign: "center"
                            font_style: "Caption"

                        MDLabel:
                            id: following_count
                            halign: "center"
                            font_style: "H6"
                            bold: True

                MDRectangleFlatIconButton:
                    icon: "pencil"
                    text: "Profili Düzenle"
                    size_hint_x: 1
                    pos_hint: {"center_x": .5}
                    on_release: root.open_edit_dialog()

                MDRectangleFlatIconButton:
                    icon: "logout"
                    text: "Çıkış Yap"
                    size_hint_x: 1
                    pos_hint: {"center_x": .5}
                    on_release: root.logout()

                MDLabel:
                    text: "Vibe'larım"
                    font_style: "H6"
                    size_hint_y: None
                    height: "30dp"
                    padding: ["10dp", "0dp"]

                MDGridLayout:
                    id: my_vibe_grid
                    cols: 3
                    adaptive_height: True
                    spacing: "5dp"
                    padding: "10dp"

<OtherProfileScreen>:
    name: "other_profile"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Profil"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'main')]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: "20dp"
                spacing: "20dp"

                MDIconButton:
                    id: target_avatar
                    icon: "account-circle"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    pos_hint: {"center_x": .5}
                    font_size: "80sp"
                    size_hint: None, None
                    size: "100dp", "100dp"

                MDLabel:
                    id: target_name
                    halign: "center"
                    bold: True
                    font_style: "H5"

                MDLabel:
                    id: target_bio
                    halign: "center"
                    font_style: "Body1"

                MDLabel:
                    id: target_location
                    halign: "center"
                    font_style: "Caption"

                MDBoxLayout:
                    padding: "10dp"
                    spacing: "20dp"

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: "5dp"

                        MDLabel:
                            text: "Vibe"
                            halign: "center"
                            font_style: "Caption"

                        MDLabel:
                            id: target_post_count
                            halign: "center"
                            font_style: "H6"
                            bold: True

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: "5dp"

                        MDLabel:
                            text: "Takipçi"
                            halign: "center"
                            font_style: "Caption"

                        MDLabel:
                            id: target_follower_count
                            halign: "center"
                            font_style: "H6"
                            bold: True

                MDBoxLayout:
                    adaptive_height: True
                    spacing: "10dp"
                    padding: "20dp"

                    MDRaisedButton:
                        id: follow_btn
                        text: "Takip Et"
                        size_hint_x: 0.5
                        on_release: root.toggle_follow()

                    MDRaisedButton:
                        text: "Mesaj At"
                        size_hint_x: 0.5
                        on_release: root.start_chat()

                MDLabel:
                    text: "Vibe'lar"
                    font_style: "H6"
                    size_hint_y: None
                    height: "30dp"
                    padding: ["10dp", "0dp"]

                MDGridLayout:
                    id: target_vibe_grid
                    cols: 3
                    adaptive_height: True
                    spacing: "5dp"
                    padding: "10dp"

<MessageListScreen>:
    name: "msg_list"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Mesajlarım"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'main')]]

        ScrollView:
            MDList:
                id: room_list
'''

if __name__ == "__main__":
    VibeApp().run()
