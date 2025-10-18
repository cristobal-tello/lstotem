import { Controller } from '@hotwired/stimulus'
import JSConfetti from 'js-confetti'

export default class extends Controller {
    connect() {
        this.jsConfetti = new JSConfetti()
        this.launch()
    }

    launch() {
        this.jsConfetti.addConfetti({
            emojis: ['🎉', '✨', '🎊', '💫'],
            confettiNumber: 50,
        })
    }
}
