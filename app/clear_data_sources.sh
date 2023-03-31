sqlite3 ~/.gerev/storage/db.sqlite3 'delete from data_source where id in (select id from data_source);'
