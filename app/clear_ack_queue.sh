sqlite3 ~/.gerev/storage/tasks.sqlite3/data.db 'delete from ack_queue_task where _id in (select _id from ack_queue_task);'
