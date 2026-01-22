import paramiko
import time
import random
import string

# ==========================================
# WINDOWS SSH BRUTE FORCE (REVISI SLOW & RANDOM)
# ==========================================

# Ganti dengan IP VM kamu
TARGET_IP = "YOUR_IP" 

USERNAMES = ["admin", "hackernetral", "support", "hacker", "hackerjahatbanget", "userbaik"]
JUMLAH_SERANGAN = 20

def generate_random_pass():
    # Membuat password acak biar PASTI SALAH dan tidak mungkin login
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def run_attack():
    print(f"\n🔥 MEMULAI SERANGAN KE: {TARGET_IP}")
    print("------------------------------------------------")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for i in range(1, JUMLAH_SERANGAN + 1):
        user = random.choice(USERNAMES)
        bad_pass = generate_random_pass()
        
        print(f"[{i}/{JUMLAH_SERANGAN}] User: '{user}' | Pass: '{bad_pass}'...", end=" ")
        
        try:
            # Timeout diperbesar sedikit
            ssh.connect(TARGET_IP, username=user, password=bad_pass, timeout=5, banner_timeout=200)
            
            # Kalau berhasil, berarti aneh banget
            print("⚠️ LOGIN SUKSES (Bahaya!)")
            ssh.close()
            
        except paramiko.AuthenticationException:
            # INI YANG KITA CARI
            print("✅ Gagal (Log Terkirim)")
            
        except Exception as e:
            # Kalau koneksi diputus server
            print(f"❌ Error Koneksi (Server menolak)")

        # JEDA DIPERLAMA: 2 Detik
        # Agar server sempat nulis log dan tidak memblokir koneksi kita
        time.sleep(2)

    print("------------------------------------------------")
    print("💀 Selesai. Tunggu notifikasi dalam 1-2 menit.")

if __name__ == "__main__":
    run_attack()