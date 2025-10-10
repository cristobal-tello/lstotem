FROM php:8.3.6-apache

WORKDIR /var/www/html

# Install necessary tools (kept for general utility like curl, git)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    unzip \
    libsqlite3-dev \
    libicu-dev \
 && rm -rf /var/lib/apt/lists/*

# Install PHP extensions
RUN docker-php-ext-install -j "$(nproc)" opcache pdo pdo_mysql mysqli bcmath pdo_sqlite intl

# Xdebug configuration (commented out as in original)
# RUN pecl install xdebug \
#  && docker-php-ext-enable xdebug \
#  && { \
#       echo "; ==== XDEBUG (dev) ===="; \
#       echo "xdebug.mode=debug,develop"; \
#       echo "xdebug.start_with_request=yes"; \
#       echo "xdebug.discover_client_host=1"; \
#       echo "xdebug.client_host=host.docker.internal"; \
#       echo "xdebug.client_port=9003"; \
#     } > "$PHP_INI_DIR/conf.d/99-xdebug.ini"

EXPOSE 9003

ENV DATABASE_URL=""

# Apply PHP specific settings
RUN set -ex; \
  { \
    echo "memory_limit = -1"; \
    echo "max_execution_time = 0"; \
    echo "upload_max_filesize = 32M"; \
    echo "post_max_size = 32M"; \
    echo "opcache.enable = Off"; \
    echo "opcache.validate_timestamps = On"; \
    echo "opcache.memory_consumption = 32"; \
  } > "$PHP_INI_DIR/conf.d/cloud-run.ini"

# Copy your local files (including index.html) into the working directory /var/www/html
COPY . ./

# *** Configuration Changes for Simple Static Serving ***

# We remove the APACHE_DOCUMENT_ROOT environment variable and all the sed commands
# related to changing the DocumentRoot, letting it default to /var/www/html.

ENV PORT=8081
ENV APP_ENV=dev
ENV LOG_LEVEL=debug
ENV APP_DEBUG=1

# 1. Update listening port
RUN sed -i "s/80/${PORT}/g" /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf
RUN mv "$PHP_INI_DIR/php.ini-development" "$PHP_INI_DIR/php.ini"

# 2. Fix for 403 Forbidden/AllowOverride if you had .htaccess in the root
# The DocumentRoot is now /var/www/html, so we apply the override there.
RUN echo " \n\
# Custom Directory Configuration for Application Root \n\
<Directory /var/www/html> \n\
    Options Indexes FollowSymLinks \n\
    AllowOverride All \n\
    Require all granted \n\
</Directory>" >> /etc/apache2/apache2.conf

# 3. Enable rewrite module (kept in case you add simple PHP routing later)
RUN a2enmod rewrite

# 4. Remove Composer installation and framework-specific commands
# RUN curl -fsSL https://getcomposer.org/composer.phar -o /usr/bin/composer && chmod +x /usr/bin/composer
# RUN composer install --no-interaction
# RUN php bin/console cache:clear

# Set permissions for the Apache user
RUN chown -R www-data:www-data /var/www/html

EXPOSE ${PORT}

CMD ["apache2-foreground"]
