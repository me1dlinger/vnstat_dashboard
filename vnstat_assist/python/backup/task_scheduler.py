from apscheduler.schedulers.blocking import BlockingScheduler
from vnstat_backup import main

def job():
    try:
        main()
    except Exception as e:
        print(f"任务执行失败: {e}")

if __name__ == "__main__":
    job()
    scheduler = BlockingScheduler()
    scheduler.add_job(job, 'cron', hour=1, minute=0, timezone="Asia/Shanghai")
    scheduler.start()