import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, borderRadius, shadows } from '../utils/theme';

interface PlayButtonProps {
  isPlaying?: boolean;
  onPress: () => void;
  size?: 'small' | 'medium' | 'large';
  style?: ViewStyle;
}

const PlayButton: React.FC<PlayButtonProps> = ({
  isPlaying = false,
  onPress,
  size = 'medium',
  style,
}) => {
  const sizeConfig = {
    small: { button: 40, icon: 20 },
    medium: { button: 56, icon: 28 },
    large: { button: 72, icon: 36 },
  };

  const { button: buttonSize, icon: iconSize } = sizeConfig[size];

  return (
    <TouchableOpacity
      style={[
        styles.button,
        {
          width: buttonSize,
          height: buttonSize,
          borderRadius: buttonSize / 2,
        },
        style,
      ]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <Ionicons
        name={isPlaying ? 'pause' : 'play'}
        size={iconSize}
        color={colors.background}
        style={!isPlaying && { marginLeft: 3 }}
      />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.md,
  },
});

export default PlayButton;

