1. Install miniconda

   ````shell
   mkdir -p ~/miniconda3 
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
   bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
   rm -rf ~/miniconda3/miniconda.sh
   ~/miniconda3/bin/conda init bash
   ~/miniconda3/bin/conda init zsh
   ````


2. Install apache2:
   ````shell
   sudo apt-get update
   sudo apt-get install apache2
   ````
3. Configure mod_wsgi (https://github.com/GrahamDumpleton/mod_wsgi/issues/378): With conda we can't use linux distribution of mod_wsgi!!
   - Install mod_wsgi in conda:
     ````bash
     conda install -c conda-forge mod_wsgi
     ````
   - With root user run: 
     ````bash
     mod_wsgi-express module-config
     ````
   
   - add two lines ``/etc/apache2/mods-available/wsgi.load``
   - create folder for operation: ``mkdir /var/run/wsgi``
   - Load module and restart apache service:
     ````bash
     a2enmod wsgi
     systemctl restart apache2
     ````
   
4. Install postgresql and timescaledb

   ````bash 
   apt install gnupg postgresql-common apt-transport-https lsb-release wget
   /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
   echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" > /etc/apt/sources.list.d/timescaledb.list
   wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | apt-key add -
   apt update
   apt install timescaledb-2-postgresql-14
   ````

5. Tune timescaleDB: 
   1. Run tuning tool
       ````bash
       timescaledb-tune --quiet --yes
       ````
   2. Restart service: 
       ````bash 
       service postgresql restart
       ````
6. Configure Database
   1. Create database
       ````SQL 
       CREATE DATABSE <name>
       ````
   2. Add timescale extension:
      ````SQL
      CREATE EXTENSION IF NOT EXISTS timescaledb;
      ````
   3. Create user: 
      ````SQL
      CREATE USER abd_db_user WITH PASSWORD '<your pwd>'
      ````
   4. Grant priviledges to new user 
      ````SQL
      GRANT ALL PRIVILEGES on DATABASE <db_name> TO abd_user;
      ````
7. Clone repository
8. Setup conda environment
9. configure config.json
10. Apply initial migrations
11. Configure Apache2 webserver
````apache
      
       <Directory /var/www/html/ABD_Webapp/ABD_Webapp>
                <Files wsgi.py>
                        Require all granted
                </Files>
        </Directory>

        WSGIDaemonProcess abd python-path=/var/www/html/ABD_Webapp python-home=/env/abd_env
        WSGIProcessGroup abd
        WSGIScriptAlias / /var/www/html/ABD_Webapp/ABD_Webapp/wsgi.py


        Alias /static /var/www/html/ABD_Webapp/static
        <Directory /var/www/html/ABD_Webapp/static>
                Require all granted
        </Directory>

        Alias /logs /var/www/html/ABD_Webapp/logs
        <Directory /var/www/html/ABD_Webapp/logs>
                Require all granted
        </Directory>

        Alias /media /var/www/html/media
        <Directory /var/www/html/ABD_Webapp/media>
                Require all granted
        </Directory>
````  
   - outside Virtual host:   WSGISocketPrefix /var/run/wsgi
12. priviledges to folders
   ````bash
   chown -R www-data /opt/ABD_Webapp/
   chown -R www-data /var/run/wsgi/
   ````
13. Configure SSL
    1. non SSL .conf
      ````apache2
      RewriteEngine On
      RewriteCond %{SERVER_PORT} !^443$
      RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]

      RewriteCond %{SERVER_NAME} =<server_name>
      RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
      ```` 
    /usr/share/doc/apache2/README.Debian.gz
14. task limits
15. WSGIApplicationGroup %{GLOBAL}