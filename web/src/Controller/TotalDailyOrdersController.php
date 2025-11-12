<?php

namespace App\Controller;

use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class TotalDailyOrdersController extends BaseController
{
    #[Route('/TotalDailyOrders', name: 'app_total_daily_orders')]
    public function index(Request $request): Response
    {
        $total = $request->query->get('total');
        return $this->render('total_daily_orders/index.html.twig', [
            'total' => $total,
        ]);
    }
}
