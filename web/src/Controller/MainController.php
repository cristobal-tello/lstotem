<?php

namespace App\Controller;

use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\DependencyInjection\ParameterBag\ParameterBagInterface;

final class MainController extends AbstractController
{
    #[Route('/', name: 'app_main')]
    public function index(ParameterBagInterface $params, string $pusherAppKey, string $pusherCluster, string $pusherChannel): Response
    {
        return $this->render('main/index.html.twig', [
            'pusher_app_key' => $pusherAppKey,
            'pusher_cluster' => $pusherCluster,
            'pusher_channel' => $pusherChannel,
        ]);
    }
}
