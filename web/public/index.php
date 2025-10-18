<?php

use App\Kernel;

require_once dirname(__DIR__) . '/vendor/autoload_runtime.php';

return function (array $context) {
    $env = getenv('APP_ENV');
    if ($env === false) {
        $env = $context['APP_ENV'] ?? 'dev';
    }

    $debug = getenv('APP_DEBUG');
    if ($debug === false) {
        $debug = $context['APP_DEBUG'] ?? 1;
    }

    return new Kernel($env, (bool) $debug);
};