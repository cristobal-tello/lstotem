<?php

namespace App\Controller;

use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;

/**
 * BaseController provides common functionality for other controllers,
 * such as automatically injecting Pusher credentials into Twig templates.
 */
class BaseController extends AbstractController
{
    public function __construct(
        private string $pusherAppKey,
        private string $pusherCluster,
        private string $pusherChannel
    ) {
    }

    /**
     * Renders a view and automatically adds common Pusher parameters to the template context.
     */
    protected function render(string $view, array $parameters = [], ?Response $response = null): Response
    {
        $parameters = array_merge(
            $parameters,
            [
                'pusher_app_key' => $this->pusherAppKey,
                'pusher_cluster' => $this->pusherCluster,
                'pusher_channel' => $this->pusherChannel,
            ]
        );

        return parent::render($view, $parameters, $response);
    }
}
