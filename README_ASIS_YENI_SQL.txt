ASIS - yeni SQL test quruluşu

Bu versiyada db.py aşağıdakı bazaya qoşulur:
  database = asis_new_db
  user     = asis_app

Məqsəd:
1) Əsas MySQL-də ayrıca yeni ASIS bazası yaratmaq.
2) Proqramı bu yeni bazada test etmək.
3) JSON backup-u proqramın öz Import bölməsindən bərpa etmək.
4) Hər şey işləsə GitHub-a push, serverdə git pull edib yeni bazaya keçmək.

Quraşdırma:
1. MySQL root ilə SQL_SETUP_ASIS_NEW_DB.sql faylını import et.
2. Proqramı aç.
3. Supervisor/Admin paneldə Backup/Import hissəsindən backup_20260604.json faylını import et.

Vacib:
- SQL_SETUP_ASIS_NEW_DB.sql köhnə asis_db-ni silmir.
- Köhnə server datasına toxunmur.
- JSON import etdikdə yalnız qoşulduğun yeni bazadakı cədvəllər təmizlənib backup datası yazılır.
- Real serverdə final keçiddən əvvəl mütləq ayrıca SQL dump götür.
