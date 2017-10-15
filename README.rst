饭否手机版复刻
==============

.. image:: https://img.shields.io/travis/akgnah/fanfou-m/master.svg
    :target: https://travis-ci.org/akgnah/fanfou-m

.. image:: https://img.shields.io/badge/code_style-pep8-orange.svg
    :target: https://www.python.org/dev/peps/pep-0008

这是我学习饭否 API 时对 `饭否手机版 <https://m.fanfou.com/>`_ 的模仿，是 2012 年的老代码，
翻出来修修补补作为使用 `fanfou-py  <https://github.com/akgnah/fanfou-py/>`_ 的一个 Demo。
Demo 效果可点这里 http://m.setq.me 查看。

环境
----

使用 Python 2.7，在 ArchLinux、Ubuntu 16.04 和 Windows 10 测试通过。

安装依赖
--------

.. code-block:: bash

   $ sudo pip install web.py
   $ sudo pip install fanfou


修改配置
--------

1. 修改 add_consumer.py 文件，把你自己的 Consumer Key 和 Consumer Secret 填进 consumers 中，可填写多个，按照文件中的格式（字典）。
   若你没有 Consumer， 可访问 `饭否应用 <https://fanfou.com/apps>`_ 页面新建一个。

2. 修改 main.py 文件中第 98 行的 client = fanfou.XAuth(consumer, 'username', 'password')，把 username 和 password 替换成你的 ID 和 密码，
   该项修改为可选，这里是为了能获取你的 Consumer 的名字，并在设置页面中显示。

运行
----
代码在 Python 2.7 中测试通过

初次运行时需要把 consumer 添加进数据库

.. code-block:: bash

   $ python add_consumer.py

运行主程序

.. code-block:: bash

   $ python main.py

然后访问 http://127.0.0.1:8080 即可。


其他说明
--------

`web.py <http://webpy.org>`_ 是一个简洁的 Python Web 框架，得益于它的简单，该项目的结构也不复杂。

main.py 是主程序，对饭否 API 的调用都在该文件中，urls.py 存着访问路径对类的映射，cache.py 是为了缓存一些 API 请求，models.py 是对数据库的一些操作。

项目对饭否手机版的模仿度很高，除了 “和他的对话” 这个功能因 API 没有提供而无法实现，采用了 “和他的私信” 代替。
项目的 url 结构和饭否手机版的 url 结构也高度一致，为了保持一致可能做了一些比较奇怪的动作，比如缓存照片列表。

若你主要想参考饭否 API 的用法，那么主要看 main.py 即可，对 cache.py 的一些动作可忽略。

致谢
----

如果你有任何疑问欢迎 Email 联系我，在我的 Github 主页能找到我的邮箱地址。感谢关注。
