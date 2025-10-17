<?php

namespace App\Controller;

use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\DependencyInjection\ParameterBag\ParameterBagInterface;

final class MainController extends AbstractController
{
    #[Route('/', name: 'app_main')]
    public function index(ParameterBagInterface $params): Response
    {
      //  dump($params->get('kernel.debug'));
        //exit;
        return $this->render('main/index.html.twig', [
            'controller_name' => 'MainController',
        ]);
    }
}
