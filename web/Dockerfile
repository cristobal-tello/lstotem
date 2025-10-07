FROM php:8.3.6-apache

WORKDIR /var/www/html

RUN apt-get update && apt-get install -y \
    git \
    curl \
    unzip \
    libsqlite3-dev \
    libicu-dev \
 && rm -rf /var/lib/apt/lists/*

RUN docker-php-ext-install -j "$(nproc)" opcache pdo pdo_mysql mysqli bcmath pdo_sqlite intl

# Xdebug for dev
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

# Optional, Xdebug uses outbound connection
EXPOSE 9003

ENV DATABASE_URL=""

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

COPY . ./

ENV APACHE_DOCUMENT_ROOT=/var/www/html/public
ENV PORT=8081
ENV APP_ENV=dev
ENV LOG_LEVEL=debug
ENV APP_DEBUG=1

RUN sed -i "s/80/${PORT}/g" /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf
RUN mv "$PHP_INI_DIR/php.ini-development" "$PHP_INI_DIR/php.ini"
RUN sed -ri -e "s!/var/www/html!${APACHE_DOCUMENT_ROOT}!g" /etc/apache2/sites-available/*.conf
RUN sed -ri -e "s!/var/www/!${APACHE_DOCUMENT_ROOT}!g" /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

RUN a2enmod rewrite

RUN curl -fsSL https://getcomposer.org/composer.phar -o /usr/bin/composer && chmod +x /usr/bin/composer

RUN chown -R www-data:www-data /var/www/html

RUN composer install --no-interaction
RUN php bin/console cache:clear

EXPOSE ${PORT}

CMD ["apache2-foreground"]
