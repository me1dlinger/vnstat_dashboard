from apscheduler.schedulers.blocking import BlockingScheduler
from vnstat_backup import main, backup_last_month, organize_backup_files, JSON_DIR


def daily_job():
    try:
        main()
    except Exception as e:
        print(f"天备份任务执行失败: {e}")


def monthly_job():
    try:
        backup_last_month()
    except Exception as e:
        print(f"月备份任务执行失败: {e}")


if __name__ == "__main__":
    organize_backup_files(JSON_DIR)
    daily_job()
    monthly_job()
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, "cron", hour=1, minute=0, timezone="Asia/Shanghai")
    scheduler.add_job(
        monthly_job, "cron", day=1, hour=0, minute=30, timezone="Asia/Shanghai"
    )
    scheduler.start()
