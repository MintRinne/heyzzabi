# PyMySQL을 MySQLdb 인터페이스로 등록 — mysqlclient(C 확장, Windows 빌드 이슈) 대신
# 순수 파이썬 드라이버를 쓰기 위함. Django의 MySQL 백엔드는 MySQLdb API를 기대하므로
# 프로세스 시작 시점에 한 번 교체해준다.
import pymysql

pymysql.install_as_MySQLdb()
