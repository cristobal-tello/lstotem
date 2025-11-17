<?php

namespace App\Controller;

use Symfony\Component\ErrorHandler\Debug;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class TotalDailyOrdersController extends BaseController
{
    #[Route('/total-daily-orders', name: 'app_total_daily_orders')]
    public function index(Request $request): Response
    {
        $total = $request->query->get('total', 0);
        return $this->render('total_daily_orders/index.html.twig', [
            'total' => $total,
        ]);
    }
}
