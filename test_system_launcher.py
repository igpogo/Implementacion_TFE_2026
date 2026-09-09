import unittest
from unittest.mock import patch
from system_launcher import run_launcher

class TestSystemLauncher(unittest.TestCase):

    @patch('system_launcher.time.sleep')
    @patch('system_launcher.run_single_cycle')
    def test_launcher_execution_loop(self, mock_run_cycle, mock_sleep):
        # Simulamos que al llegar al sleep en la primera vuelta, el usuario presiona Ctrl+C
        mock_sleep.side_effect = KeyboardInterrupt
        
        # Ejecutamos el lanzador indicando 3 minutos de intervalo
        run_launcher(intervalo_minutos=3)
        
        # Verificamos que invocó al demonio exactamente una vez antes del corte
        mock_run_cycle.assert_called_once()
        
        # Verificamos que convirtió los 3 minutos a 180 segundos para el sleep
        mock_sleep.assert_called_once_with(180)

if __name__ == "__main__":
    unittest.main()