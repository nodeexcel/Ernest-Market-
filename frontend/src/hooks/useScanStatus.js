import { usePolling } from './usePolling';
import { scanApi } from '../services/api';

export function useScanStatus(fastPoll = false) {
  return usePolling(scanApi.getStatus, fastPoll ? 2000 : 4000, true);
}
