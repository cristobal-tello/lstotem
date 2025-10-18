import { Controller } from '@hotwired/stimulus'
import TmOdometer from 'tm-odometer'
import 'tm-odometer/themes/odometer-theme-car.css'

export default class extends Controller {
    static values = {
        value: Number,
        duration: Number
    }

    connect() {
        if (!this.element) {
            console.log("Cannot connect in odometer");
            return
        }

        try {
            document.body.style.overflowX = 'hidden';
            this.odometer = new TmOdometer({
                el: this.element,
                value: 0,
                duration: this.durationValue || 2000,
                format: '(dddd)',
                theme: 'car',
                animation: 'count',
            })
            setTimeout(() => this.updateValue(), 300)
        } catch (error) {
            console.error('Error odometer:', error)
        }
    }

    updateValue() {
        if (this.odometer && this.valueValue != null) {
            console.log(this.valueValue);
            this.odometer.update(this.valueValue)
        }
    }

    disconnect() {
        this.odometer = null
    }
}
