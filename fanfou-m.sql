create table sessions (
  session_id blob(128) unique not null,
  atime timestamp not null default current_timestamp,
  data text
);
create table consumer (
  consumer_id blob(128) primary key,
  consumer_name blob(512),
  consumer blob(512),
  consumer_type blob(128)
);
create table token (
  token_id blob(128) primary key,
  consumer_id blob(128),
  token blob(512),
  FOREIGN key(consumer_id) references consumer(consumer_id)
);
create table conf (
  user_id blob(128) primary key,
  blacklist text
);
create table log (
  atime datetime not null default (datetime(current_timestamp, 'localtime')),
  referer text,
  exc_info text
);
create table ctx (
  key blob(128) primary key,
  val text
);
