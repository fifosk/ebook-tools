export type ImageApiNodeOption = {
  value: string;
  label: string;
  defaultActive?: boolean;
};

export const IMAGE_API_NODE_OPTIONS: ImageApiNodeOption[] = [
  {
    value: 'http://192.168.1.9:7860',
    label: 'Mac Studio (192.168.1.9:7860)',
    defaultActive: true
  },
  {
    value: 'http://192.168.1.157:7860',
    label: 'MacBook Air (192.168.1.157:7860)',
    defaultActive: true
  },
  {
    value: 'http://192.168.1.76:7860',
    label: 'Ipad Pro (192.168.1.76:7860)',
    defaultActive: true
  }
];

export const DEFAULT_IMAGE_API_BASE_URLS = IMAGE_API_NODE_OPTIONS.filter(
  (option) => option.defaultActive
).map((option) => option.value);
