import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


class ServerDB:
    Base = declarative_base()

    class Client(Base):
        __tablename__ = 'clients'

        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)
        last_conn = Column(DateTime)

        active_users = relationship("ActiveClient", back_populates="client")
        history = relationship("ClientHistory", back_populates="user")

        def __repr__(self):
            return f'<Client(name={self.login})>'


    class ActiveClient(Base):
        __tablename__ = 'active_clients'
        id = Column(Integer, primary_key=True)
        client_id = Column(Integer, ForeignKey('clients.id'), unique=True)
        address = Column(String)
        port = Column(String)
        login_time = Column(DateTime)

        client = relationship("Client", back_populates="active_users")

        def __repr__(self):
            return f'<ActiveClient({self.client_id}, {self.address}:{self.port})>'


    class ClientHistory(Base):
        __tablename__ = 'client_history'

        id = Column(Integer, primary_key=True)
        client_id = Column(Integer, ForeignKey('clients.id'))
        ip_address = Column(String)
        port = Column(String)
        last_conn = Column(DateTime)

        user = relationship("Client", back_populates="history")

        def __repr__(self):
            return f'<ClientHistory({self.ip_address}, {self.date_time})>'


    def __init__(self):
        self.engine = create_engine('sqlite:///server_base.db', echo=False, pool_recycle=7200)
        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.session.query(self.ActiveClient).delete()
        self.session.commit()

    def user_login(self, username, ip_address, port):
        rez = self.session.query(self.Client).filter_by(login=username)
        if rez.count():
            user = rez.first()
            user.last_conn = datetime.datetime.now()
        else:
            user = self.Client(username)
            self.session.add(user)
            self.session.commit()
        new_active_user = self.ActiveClient(client_id=user.id, address=ip_address, port=port, login_time=datetime.datetime.now())
        self.session.add(new_active_user)
        self.history = self.ClientHistory(client_id=user.id, ip_address=ip_address, port=port, last_conn=datetime.datetime.now())
        self.session.add(history)
        self.session.commit()

    def user_logout(self, username):
        user = self.session.query(self.Client).filter_by(login=username).first()
        self.session.query(self.ActiveClient).filter_by(client_id=user.id).delete()
        self.session.commit()

    def users_list(self):
        query = self.session.query(self.Client.login, self.Client.last_conn)
        return query.all()

    def active_users_list(self):
        query = self.session.query(self.Client.login, self.ActiveClient.address, self.ActiveClient.port, self.ActiveClient.login_time).join(self.Client)
        return query.all()

    def login_history(self, username=None):
        query = self.session.query(self.Client.login, self.ClientHistory.last_conn, self.ClientHistory.ip_address, self.ClientHistory.port).join(self.Client)
        if username:
            query = query.filter(self.Client.login==username)
        return query.all()


if __name__ == '__main__':
    db = ServerDB()
    db.user_login('client_1', '192.168.1.4', 8888)
    db.user_login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print(db.active_users_list())
    # выполянем 'отключение' пользователя
    db.user_logout('client_1')
    print(db.users_list())
    # выводим список активных пользователей
    print(db.active_users_list())
    db.user_logout('client_2')
    print(db.users_list())
    print(db.active_users_list())

    # запрашиваем историю входов по пользователю
    # db.login_history('client_1')
    # # выводим список известных пользователей
    # print(db.users_list())
