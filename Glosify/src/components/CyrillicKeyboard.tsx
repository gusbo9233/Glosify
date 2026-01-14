import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius } from '../utils/theme';

interface CyrillicKeyboardProps {
  onKeyPress: (key: string) => void;
  onBackspace: () => void;
  onClose?: () => void;
}

const CYRILLIC_LAYOUT = [
  ['й', 'ц', 'у', 'к', 'е', 'н', 'г', 'ш', 'щ', 'з', 'х', 'ъ'],
  ['ф', 'ы', 'в', 'а', 'п', 'р', 'о', 'л', 'д', 'ж', 'э'],
  ['я', 'ч', 'с', 'м', 'и', 'т', 'ь', 'б', 'ю', '.'],
];

const CYRILLIC_LAYOUT_UPPERCASE = [
  ['Й', 'Ц', 'У', 'К', 'Е', 'Н', 'Г', 'Ш', 'Щ', 'З', 'Х', 'Ъ'],
  ['Ф', 'Ы', 'В', 'А', 'П', 'Р', 'О', 'Л', 'Д', 'Ж', 'Э'],
  ['Я', 'Ч', 'С', 'М', 'И', 'Т', 'Ь', 'Б', 'Ю', '.'],
];

const CyrillicKeyboard: React.FC<CyrillicKeyboardProps> = ({
  onKeyPress,
  onBackspace,
  onClose,
}) => {
  const [isUppercase, setIsUppercase] = React.useState(false);
  const layout = isUppercase ? CYRILLIC_LAYOUT_UPPERCASE : CYRILLIC_LAYOUT;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>Cyrillic Keyboard</Text>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>
      <View style={styles.keyboard}>
        {layout.map((row, rowIndex) => (
          <View key={rowIndex} style={styles.row}>
            {row.map((key) => (
              <TouchableOpacity
                key={key}
                style={styles.key}
                onPress={() => onKeyPress(key)}
                activeOpacity={0.7}
              >
                <Text style={styles.keyText}>{key}</Text>
              </TouchableOpacity>
            ))}
            {rowIndex === layout.length - 1 && (
              <>
                <TouchableOpacity
                  style={[styles.key, styles.specialKey]}
                  onPress={() => setIsUppercase(!isUppercase)}
                  activeOpacity={0.7}
                >
                  <Ionicons
                    name={isUppercase ? 'arrow-down' : 'arrow-up'}
                    size={18}
                    color={colors.textPrimary}
                  />
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.key, styles.specialKey, styles.backspaceKey]}
                  onPress={onBackspace}
                  activeOpacity={0.7}
                >
                  <Ionicons name="backspace" size={20} color={colors.textPrimary} />
                </TouchableOpacity>
              </>
            )}
          </View>
        ))}
        <View style={styles.row}>
          <TouchableOpacity
            style={[styles.key, styles.spaceKey]}
            onPress={() => onKeyPress(' ')}
            activeOpacity={0.7}
          >
            <Text style={styles.spaceText}>Space</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  headerText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  closeButton: {
    padding: spacing.xs,
  },
  keyboard: {
    paddingHorizontal: spacing.xs,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: spacing.xs,
    gap: spacing.xs,
  },
  key: {
    minWidth: 32,
    height: 40,
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.sm,
  },
  keyText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '500',
  },
  specialKey: {
    backgroundColor: colors.background,
    minWidth: 50,
  },
  backspaceKey: {
    minWidth: 60,
  },
  spaceKey: {
    flex: 1,
    minWidth: '100%',
    maxWidth: '100%',
  },
  spaceText: {
    color: colors.textPrimary,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
});

export default CyrillicKeyboard;
